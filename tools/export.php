<?php
/**
 * 临时数据导出端点（同步时上传，取完立即删除）。
 *
 * 用途：虚拟主机只给 FTP，无法执行 mysqldump，因此用这个脚本从活库读出最新数据。
 * 安全：必须带正确 token（由 tools/sync.py 生成并替换 __TOKEN__），否则一律 404；
 *       文件名随机，用完即删，不在服务器上常驻。
 */
$TOKEN = '__TOKEN__';

$given = isset($_GET['k']) && is_string($_GET['k']) ? $_GET['k'] : '';
$ok = function_exists('hash_equals') ? hash_equals($TOKEN, $given) : ($TOKEN === $given);
if (!$ok) {
    header('HTTP/1.1 404 Not Found');
    header('Content-Type: text/plain');
    echo "Not Found\n";
    exit;
}

@set_time_limit(900);
@ini_set('memory_limit', '256M');

// 注意：主机是 PHP 5.2，没有 __DIR__ 常量，必须用 dirname(__FILE__)
require dirname(__FILE__) . '/config.php';   // emlog: DB_HOST / DB_USER / DB_PASSWD / DB_NAME

$prefix = defined('DB_PREFIX') ? DB_PREFIX : 'emlog_';
$pun_prefix = '';
$pun_cfg = dirname(__FILE__) . '/forum/config.php';
if (is_file($pun_cfg)) {
    include $pun_cfg;                // PunBB: $db_host/$db_name/$db_username/$db_password/$db_prefix
    if (isset($db_prefix)) {
        $pun_prefix = $db_prefix;
    }
}

/**
 * 剔掉非法 UTF-8 字节。老数据里混进了坏字节，而 PHP 5.2 的 json_encode
 * 碰到非 UTF-8 会直接返回 false。
 */
function wx_utf8_fix($s) {
    $out = '';
    $len = strlen($s);
    $i = 0;
    while ($i < $len) {
        $c = ord($s[$i]);
        if ($c < 0x80) { $out .= $s[$i]; $i++; continue; }
        if ($c >= 0xC2 && $c <= 0xDF) { $n = 1; }
        elseif ($c >= 0xE0 && $c <= 0xEF) { $n = 2; }
        elseif ($c >= 0xF0 && $c <= 0xF4) { $n = 3; }
        else { $i++; continue; }
        $seq = $s[$i];
        $ok = true;
        for ($j = 1; $j <= $n; $j++) {
            if ($i + $j >= $len) { $ok = false; break; }
            $cc = ord($s[$i + $j]);
            if ($cc < 0x80 || $cc > 0xBF) { $ok = false; break; }
            $seq .= $s[$i + $j];
        }
        if ($ok) { $out .= $seq; $i += $n + 1; } else { $i++; }
    }
    return $out;
}

/* PHP 5.2 的 json_encode 只接受一个参数（第二个参数是 5.3 才加的），
   且中文会被转义成 uXXXX 形式——合法 JSON，只是体积大一些。 */
function wx_json($row) {
    $json = json_encode($row);
    if ($json === false || $json === 'null') {
        $clean = array();
        foreach ($row as $k => $v) {
            $clean[$k] = is_string($v) ? wx_utf8_fix($v) : $v;
        }
        $json = json_encode($clean);
    }
    return $json === false ? 'null' : $json;
}

$db = @new mysqli(DB_HOST, DB_USER, DB_PASSWD, DB_NAME);
if ($db->connect_errno) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('error' => 'db connect failed: ' . $db->connect_error));
    exit;
}
$db->set_charset('utf8');

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex');

$since = isset($_GET['since']) ? (int) $_GET['since'] : 0;
// 每项是 array(列名, 比较运算符, 值)，null 表示整表导出
$tables = array(
    // emlog 博客：可增量（since>0 时只取更新的）
    $prefix . 'blog'       => $since > 0 ? array('date', '>', $since) : null,
    $prefix . 'comment'    => $since > 0 ? array('date', '>', $since) : null,
    $prefix . 'user'       => null,
    $prefix . 'sort'       => null,
    $prefix . 'tag'        => null,
    $prefix . 'attachment' => null,
    $prefix . 'options'    => null,
    $prefix . 'navi'       => null,
    // PunBB 论坛：真实帖都早于 2022，垃圾潮（7.8 万条阿拉伯语广告帖）一律不要
    $pun_prefix . 'topics'     => array('posted', '<', 1640995200),
    $pun_prefix . 'posts'      => array('posted', '<', 1640995200),
    $pun_prefix . 'users'      => null,
    $pun_prefix . 'forums'     => null,
    $pun_prefix . 'categories' => null,
);

echo '{"generated_at":' . time() . ',"php":"' . PHP_VERSION . '","since":' . $since . ',"tables":{';
$first_table = true;
foreach ($tables as $table => $filter) {
    if (!preg_match('/^[A-Za-z0-9_]+$/', $table)) {
        continue;
    }
    $sql = 'SELECT * FROM `' . $table . '`';
    if ($filter !== null && $filter[2] > 0) {
        $sql .= ' WHERE `' . $filter[0] . '` ' . $filter[1] . ' ' . (int) $filter[2];
    }
    $res = @$db->query($sql);
    if (!$res) {
        continue;   // 表不存在就跳过，保证整体不失败
    }
    echo ($first_table ? '' : ',') . wx_json($table) . ':[';
    $first_row = true;
    while ($row = $res->fetch_assoc()) {
        $json = wx_json($row);
        if ($json === 'null') {
            continue;
        }
        echo ($first_row ? '' : ',') . $json;
        $first_row = false;
    }
    $res->free();
    echo ']';
    $first_table = false;
}
echo '}}';
$db->close();
