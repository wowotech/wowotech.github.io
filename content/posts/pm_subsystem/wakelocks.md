---
title: "Linux电源管理(9)_wakelocks"
date: 2014-09-14T23:17:28+08:00
url: "/pm_subsystem/wakelocks.html"
gid: "89"
emlog_type: "blog"
summary: "\r\n\twakelocks是一个有故事的功能。\r\n\r\n\r\n\twakelocks最初出现在Android为linux kernel打的一个补丁集上，该补丁集实现了一个名称为“wakelocks”的系统调用，该系统调用允许调用者阻止系统进入低功耗模式（如idle、suspend等）。同时，该补丁集更改了Linux kernel原生的电源管理执行过程（kernel/power/main.c中的state_"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "电源管理", "wakelock", "Android"]
views: 66693
comment_count: 45
aliases:
  - "/pm_subsystem/89.html"
  - "/89.html"
---

#### 1. 前言

wakelocks是一个有故事的功能。

wakelocks最初出现在Android为linux kernel打的一个补丁集上，该补丁集实现了一个名称为“wakelocks”的系统调用，该系统调用允许调用者阻止系统进入低功耗模式（如idle、suspend等）。同时，该补丁集更改了Linux kernel原生的电源管理执行过程（kernel/power/main.c中的state\_show和state\_store），转而执行自定义的state\_show、state\_store。

这种做法是相当不规范的，它是典型的只求实现功能，不择手段。就像国内很多的Linux开发团队，要实现某个功能，都不去弄清楚kernel现有的机制、框架，牛逼哄哄的猛干一番。最后功能是实现了，可都不知道重复造了多少轮子，浪费了多少资源。到此打住，Android的开发者不会这么草率，他们推出wakelocks机制一定有一些苦衷，我们就不评论了。

但是，虽然有苦衷，kernel的开发者可是有原则的，死活不让这种机制合并到kernel分支（换谁也不让啊），直到kernel自身的wakeup events framework成熟后，这种僵局才被打破。因为Android开发者想到了一个坏点子：不让合并就不让合并呗，我用你的机制（wakeup source），再实现一个就是了。至此，全新的wakelocks出现了。

所以wakelocks有两个，早期Android版本的wakelocks几乎已经销声匿迹了，不仔细找还真找不到它的source code（这里有一个链接，但愿读者看到时还有效，[drivers/android/power.c](https://www.codeaurora.org/cgit/quic/la/kernel/common/tree/drivers/android/power.c?h=android-2.6.25)）。本文不打算翻那本旧黄历，所以就focus在新的wakelocks上（kernel/power/wakelock.c，较新的kernel都支持）。

#### 2. Android wakelocks

虽说不翻旧黄历了，还是要提一下Android wakelocks的功能，这样才能知道kernel wakelocks要做什么。总的来说，Android wakelocks提供的功能包括：

1）一个sysfs文件：/sys/power/wake\_lock，用户程序向文件写入一个字符串，即可创建一个wakelock，该字符串就是wakelock的名字。该wakelock可以阻止系统进入低功耗模式。

2）一个sysfs文件：：/sys/power/wake\_unlock，用户程序向文件写入相同的字符串，即可注销一个wakelock。

3）当系统中所有的wakelock都注销后，系统可以自动进入低功耗状态。

4）向内核其它driver也提供了wakelock的创建和注销接口，允许driver创建wakelock以阻止睡眠、注销wakelock以允许睡眠。

有关Android wakelocks更为详细的描述，可以参考下面的一个链接：

[http://elinux.org/Android\_Power\_Management](http://elinux.org/Android_Power_Management "http://elinux.org/Android_Power_Management")

#### 3. Kernel wakelocks

##### 3.1 Kernel wakelocks的功能

对比Android wakelocks要实现的功能，Linux kernel的方案是：

1）允许driver创建wakelock以阻止睡眠、注销wakelock以允许睡眠：已经由“[Linux电源管理(7)\_Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)”所描述的wakeup source取代。

2）当系统中所有的wakelock都注销后，系统可以自动进入低功耗状态：由autosleep实现（下一篇文章会分析）。

3）wake\_lock和wake\_unlock功能：由本文所描述的kernel wakelocks实现，其本质就是将wakeup source开发到用户空间访问。

##### 3.2 Kernel wakelocks在电源管理中的位置

相比Android wakelocks，Kernel wakelocks的实现非常简单（简单的才是最好的），就是在PM core中增加一个wakelock模块（kernel/power/wakelock.c），该模块依赖wakeup events framework提供的wakeup source机制，实现用户空间的wakeup source（就是wakelocks），并通过PM core main模块，向用户空间提供两个同名的sysfs文件，wake\_lock和wake\_unlock。

[![kernel wakelocks architecture](/content/uploadfile/201409/af1df09d987a9e72353c8f1dbf90e53b20140914151724.gif "kernel wakelocks architecture")](/content/uploadfile/201409/ead051b9d07758f3758e7c5f98148dc720140914151722.gif)

##### 3.3 /sys/power/wake\_lock & /sys/power/wake\_unlock

从字面意思上，新版的wake\_lock和wake\_unlock和旧版的一样，都是用于创建和注销wakelock。从应用开发者的角度，确实可以这样理解。但从底层实现的角度，却完全不是一回事。

Android的wakelock，真是一个lock，用户程序创建一个wakelock，就是在系统suspend的路径上加了一把锁，注销就是解开这把锁。直到suspend路径上所有的锁都解开时，系统才可以suspend。

而Kernel的wakelock，是基于wakeup source实现的，因此创建wakelock的本质是在指定的wakeup source上activate一个wakeup event，注销wakelock的本质是deactivate wakeup event。因此，/sys/power/wake\_lock和/sys/power/wake\_unlock两个sysfs文件的的功能就是：

写wake\_lock（以wakelock name和timeout时间<可选>为参数），相当于以wakeup source为参数调用\_\_pm\_stay\_awake（或者\_\_pm\_wakeup\_event），即activate wakeup event；

写wake\_unlock（以wakelock name为参数），相当于以wakeup source为参数，调用\_\_pm\_relax；

读wake\_lock，获取系统中所有的处于active状态的wakelock列表（也即wakeup source列表）

读wake\_unlock，返回系统中所有的处于非active状态的wakelock信息（也即wakeup source列表）。

注1：上面有关wakeup source的操作接口，可参考“[Linux电源管理(7)\_Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)”。

这两个sysfs文件在kernel/power/main.c中实现，如下：

```
 1: #ifdef CONFIG_PM_WAKELOCKS
```

```
 2: static ssize_t wake_lock_show(struct kobject *kobj,
```

```
 3: struct kobj_attribute *attr,
```

```
 4: char *buf)
```

```
 5: {
```

```
 6: return pm_show_wakelocks(buf, true);
```

```
 7: }
```

```
 8:  
```

```
 9: static ssize_t wake_lock_store(struct kobject *kobj,
```

```
 10: struct kobj_attribute *attr,
```

```
 11: const char *buf, size_t n)
```

```
 12: {
```

```
 13: int error = pm_wake_lock(buf);
```

```
 14: return error ? error : n;
```

```
 15: }
```

```
 16:  
```

```
 17: power_attr(wake_lock);
```

```
 18:  
```

```
 19: static ssize_t wake_unlock_show(struct kobject *kobj,
```

```
 20: struct kobj_attribute *attr,
```

```
 21: char *buf)
```

```
 22: {
```

```
 23: return pm_show_wakelocks(buf, false);
```

```
 24: }
```

```
 25:  
```

```
 26: static ssize_t wake_unlock_store(struct kobject *kobj,
```

```
 27: struct kobj_attribute *attr,
```

```
 28: const char *buf, size_t n)
```

```
 29: {
```

```
 30: int error = pm_wake_unlock(buf);
```

```
 31: return error ? error : n;
```

```
 32: }
```

```
 33:  
```

```
 34: power_attr(wake_unlock);
```

```
 35:  
```

```
 36: #endif /* CONFIG_PM_WAKELOCKS */
```

> 1）wakelocks功能不是linux kernel的必选功能，可以通过CONFIG\_PM\_WAKELOCKS开关。
>
> 2）wake\_lock的写接口，直接调用pm\_wake\_lock；wake\_unlock的写接口，直接调用pm\_wake\_unlock；它们的读接口，直接调用pm\_show\_wakelocks接口（参数不同）。这三个接口均在kernel/power/wakelock.c中实现。

##### 3.4 pm\_wake\_lock

pm\_wake\_lock位于kernel\power\wakelock.c中，用于上报一个wakeup event（从另一个角度，就是阻止系统suspend），代码如下：

```
 1: int pm_wake_lock(const char *buf)
```

```
 2: {
```

```
 3: const char *str = buf;
```

```
 4: struct wakelock *wl;
```

```
 5: u64 timeout_ns = 0;
```

```
 6: size_t len;
```

```
 7: int ret = 0;
```

```
 8:  
```

```
 9: if (!capable(CAP_BLOCK_SUSPEND))
```

```
 10: return -EPERM;
```

```
 11:  
```

```
 12: while (*str && !isspace(*str))
```

```
 13: str++;
```

```
 14:  
```

```
 15: len = str - buf;
```

```
 16: if (!len)
```

```
 17: return -EINVAL;
```

```
 18:  
```

```
 19: if (*str && *str != '\n') {
```

```
 20: /* Find out if there's a valid timeout string appended. */
```

```
 21: ret = kstrtou64(skip_spaces(str), 10, &timeout_ns);
```

```
 22: if (ret)
```

```
 23: return -EINVAL;
```

```
 24: }
```

```
 25:  
```

```
 26: mutex_lock(&wakelocks_lock);
```

```
 27:  
```

```
 28: wl = wakelock_lookup_add(buf, len, true);
```

```
 29: if (IS_ERR(wl)) {
```

```
 30: ret = PTR_ERR(wl);
```

```
 31: goto out;
```

```
 32: }
```

```
 33: if (timeout_ns) {
```

```
 34: u64 timeout_ms = timeout_ns + NSEC_PER_MSEC - 1;
```

```
 35:  
```

```
 36: do_div(timeout_ms, NSEC_PER_MSEC);
```

```
 37: __pm_wakeup_event(&wl->ws, timeout_ms);
```

```
 38: } else {
```

```
 39: __pm_stay_awake(&wl->ws);
```

```
 40: }
```

```
 41:  
```

```
 42: wakelocks_lru_most_recent(wl);
```

```
 43: out:
```

```
 44: mutex_unlock(&wakelocks_lock);
```

```
 45: return ret;
```

```
 46: }
```

> a）输入参数为一个字符串，如"wake\_lock\_test 1000”，该字符串指定上报wakeup event的wakelock name，可以在name后用空格隔开，添加一个时间值（单位为ns），表示该event的timeout值。
>
> b）调用capable，检查当前进程是否具备阻止系统suspend的权限。   
> 注2：capable是Linux security子系统提供的一个接口，用于权限判断。我们说过，power是系统的核心资源，理应由OS全权管理，但wakelock违反了这一原则，将阻止系统睡眠的权利给了用户空间。这样一来，用户空间程序将可以随心所欲的占用power资源，特别是用户态的程序员，天生对资源占用不敏感（这是对的），就导致该接口有被滥用的风险。不过还好，通过系统的权限管理机制，可以改善这种状态（其实不是改善，而是矛盾转移，很有可能把最终的裁决权交给用户，太糟糕了！）。
>
> c）解析字符串，将timeout值（有的话）保存在timeout\_ns中，解析name长度（len），并将name保存在原来的buf中。
>
> d）调用wakelock\_lookup\_add接口，查找是否有相同name的wakelock。如果有，直接返回wakelock的指针；如果没有，分配一个wakelock，同时调用wakeup events framework提供的接口，创建该wakelock对应的wakeup source结构。
>
> e）如果指定timeout值，以wakelock的wakeup source指针为参数，调用\_\_pm\_wakeup\_event接口，上报一个具有时限的wakeup events；否则，调用\_\_pm\_stay\_awake，上报一个没有时限的wakeup event。有关这两个接口的详细说明，可参考“[Linux电源管理(7)\_Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)”。

wakelock\_lookup\_add是内部接口，代码如下：

```
 1: static struct wakelock *wakelock_lookup_add(const char *name, size_t len,
```

```
 2: bool add_if_not_found)
```

```
 3: {
```

```
 4: struct rb_node **node = &wakelocks_tree.rb_node;
```

```
 5: struct rb_node *parent = *node;
```

```
 6: struct wakelock *wl;
```

```
 7:  
```

```
 8: while (*node) {
```

```
 9: int diff;
```

```
 10:  
```

```
 11: parent = *node;
```

```
 12: wl = rb_entry(*node, struct wakelock, node);
```

```
 13: diff = strncmp(name, wl->name, len);
```

```
 14: if (diff == 0) {
```

```
 15: if (wl->name[len])
```

```
 16: diff = -1;
```

```
 17: else
```

```
 18: return wl;
```

```
 19: }
```

```
 20: if (diff < 0)
```

```
 21: node = &(*node)->rb_left;
```

```
 22: else
```

```
 23: node = &(*node)->rb_right;
```

```
 24: }
```

```
 25: if (!add_if_not_found)
```

```
 26: return ERR_PTR(-EINVAL);
```

```
 27:  
```

```
 28: if (wakelocks_limit_exceeded())
```

```
 29: return ERR_PTR(-ENOSPC);
```

```
 30:  
```

```
 31: /* Not found, we have to add a new one. */
```

```
 32: wl = kzalloc(sizeof(*wl), GFP_KERNEL);
```

```
 33: if (!wl)
```

```
 34: return ERR_PTR(-ENOMEM);
```

```
 35:  
```

```
 36: wl->name = kstrndup(name, len, GFP_KERNEL);
```

```
 37: if (!wl->name) {
```

```
 38: kfree(wl);
```

```
 39: return ERR_PTR(-ENOMEM);
```

```
 40: }
```

```
 41: wl->ws.name = wl->name;
```

```
 42: wakeup_source_add(&wl->ws);
```

```
 43: rb_link_node(&wl->node, parent, node);
```

```
 44: rb_insert_color(&wl->node, &wakelocks_tree);
```

```
 45: wakelocks_lru_add(wl);
```

```
 46: increment_wakelocks_number();
```

```
 47: return wl;
```

```
 48: }
```

> 在wakelock.c中，维护一个名称为wakelocks\_tree的红黑树（红黑树都用上了，可以想象wakelocks曾经使用多么频繁！），所有的wakelock都保存在该tree上。因此该接口的动作是：
>
> a）查找红黑树，如果找到name相同的wakelock，返回wakelock指针。
>
> b）如果没找到，且add\_if\_not\_found为false，返回错误。
>
> c）如果add\_if\_not\_found为true，分配一个struct wakelock变量，并初始化它的名称、它的wakeup source的名称。调用wakeup\_source\_add接口，将wakeup source添加到wakeup events framework中。
>
> d）将该wakelock添加到红黑树。
>
> e）最后调用wakelocks\_lru\_add接口，将新分配的wakeup添加到一个名称为wakelocks\_lru\_list的链表前端（该功能和wakelock的垃圾回收机制有关，后面会单独描述）。

再看一下struct wakelock结构：

```
 1: struct wakelock {
```

```
 2: char *name;
```

```
 3: struct rb_node          node;
```

```
 4: struct wakeup_source    ws;
```

```
 5: #ifdef CONFIG_PM_WAKELOCKS_GC
```

```
 6: struct list_head        lru;
```

```
 7: #endif
```

```
 8: };
```

非常简单：一个name指针，保存wakelock的名称；一个rb node节点，用于组成红黑树；一个wakeup source变量；如果开启了wakelocks垃圾回收功能，一个用于GC的list head。

##### 3.5 pm\_wake\_unlock

pm\_wake\_unlock和pm\_wake\_lock类似，如下：

```
 1: int pm_wake_unlock(const char *buf)
```

```
 2: {
```

```
 3: struct wakelock *wl;
```

```
 4: size_t len;
```

```
 5: int ret = 0;
```

```
 6:  
```

```
 7: if (!capable(CAP_BLOCK_SUSPEND))
```

```
 8: return -EPERM;
```

```
 9:  
```

```
 10: len = strlen(buf);
```

```
 11: if (!len)
```

```
 12: return -EINVAL;
```

```
 13:  
```

```
 14: if (buf[len-1] == '\n')
```

```
 15: len--;
```

```
 16:  
```

```
 17: if (!len)
```

```
 18: return -EINVAL;
```

```
 19:  
```

```
 20: mutex_lock(&wakelocks_lock);
```

```
 21:  
```

```
 22: wl = wakelock_lookup_add(buf, len, false);
```

```
 23: if (IS_ERR(wl)) {
```

```
 24: ret = PTR_ERR(wl);
```

```
 25: goto out;
```

```
 26: }
```

```
 27: __pm_relax(&wl->ws);
```

```
 28:  
```

```
 29: wakelocks_lru_most_recent(wl);
```

```
 30: wakelocks_gc();
```

```
 31:  
```

```
 32: out:
```

```
 33: mutex_unlock(&wakelocks_lock);
```

```
 34: return ret;
```

```
 35: }
```

> a）输入参数为一个字符串，如"wake\_lock\_test”，该字符串指定一个wakelock name。
>
> b）调用capable，检查当前进程是否具备阻止系统suspend的权限。
>
> c）解析字符串
>
> d）调用wakelock\_lookup\_add接口，查找是否有相同name的wakelock。如果有，直接返回wakelock的指针；如果没有，退出。
>
> e）调用\_\_pm\_relax接口，deactive wakelock对应的wakeup source。
>
> f）调用wakelocks\_lru\_most\_recent接口，将盖wakelock移到wakelocks\_lru\_list链表的前端（表示它是最近一个被访问到的，和GC有关，后面重点描述）。
>
> g）调用wakelocks\_gc，执行wakelock的垃圾回收动作。

##### 3.6 pm\_show\_wakelocks

该接口很简单，查询红黑树，返回处于acvtive或者deactive状态的wakelock，如下：

```
 1: ssize_t pm_show_wakelocks(char *buf, bool show_active)
```

```
 2: {
```

```
 3: struct rb_node *node;
```

```
 4: struct wakelock *wl;
```

```
 5: char *str = buf;
```

```
 6: char *end = buf + PAGE_SIZE;
```

```
 7:  
```

```
 8: mutex_lock(&wakelocks_lock);
```

```
 9:  
```

```
 10: for (node = rb_first(&wakelocks_tree); node; node = rb_next(node)) {
```

```
 11: wl = rb_entry(node, struct wakelock, node);
```

```
 12: if (wl->ws.active == show_active)
```

```
 13: str += scnprintf(str, end - str, "%s ", wl->name);
```

```
 14: }
```

```
 15: if (str > buf)
```

```
 16: str--;
```

```
 17:  
```

```
 18: str += scnprintf(str, end - str, "\n");
```

```
 19:  
```

```
 20: mutex_unlock(&wakelocks_lock);
```

```
 21: return (str - buf);
```

```
 22: }
```

> 1）遍历红黑树，拿到wakelock指针，判断其中的wakeup source的active变量，如果和输入变量（show\_active)相符，将该wakelock的名字添加在buf中。
>
> 2）调整buf的长度和结束符，返回长度值。

##### 3.7 wakelocks的垃圾回收机制

由上面的逻辑可知，一个wakelock的生命周期，应只存在于wakeup event的avtive时期内，因此如果它的wakeup source状态为deactive，应该销毁该wakelock。但销毁后，如果又产生wakeup events，就得重新建立。如果这种建立->销毁->建立的过程太频繁，效率就会降低。

因此，最好不销毁，保留系统所有的wakelocks（同时可以完整的保留wakelock信息），但如果wakelocks太多（特别是不活动的），将会占用很多内存，也不合理。

折衷方案，保留一些非active状态的wakelock，到一定的时机时，再销毁，这就是wakelocks的垃圾回收（GC）机制。

wakelocks GC功能可以开关（由CONFIG\_PM\_WAKELOCKS\_GC控制），如果关闭，系统会保留所有的wakelocks，如果打开，它的处理逻辑也很简单：

1）定义一个list head，保存所有的wakelock指针，如下：

```
 1: static LIST_HEAD(wakelocks_lru_list);
```

```
 2: static unsigned int wakelocks_gc_count;
```

2）在wakelock结构中，嵌入一个list head（lru），用于挂入wakelocks\_lru\_list。可参考3.4小节的描述。

3）wakelocks\_lru\_list中的wakelock是按访问顺序排列的，最近访问的，靠近head位置。这是由3种操作保证的：

> a）wakelock创建时（见3.4小节），调用wakelocks\_lru\_add接口，将改wakelock挂到wakelocks\_lru\_list的head处（利用list\_add接口），表示它是最近被访问的。
>
> b）pm\_wake\_lock或者pm\_wake\_unlock时，调用wakelocks\_lru\_most\_recent接口，将该wakelcok移到链表的head处，表示最近访问。
>
> c）每当pm\_wake\_unlock时，调用wakelocks\_gc，执行wakelock的垃圾回收动作。wakelocks\_gc的实现如下：

```
 1: static void wakelocks_gc(void)
```

```
 2: {
```

```
 3: struct wakelock *wl, *aux;
```

```
 4: ktime_t now;
```

```
 5:  
```

```
 6: if (++wakelocks_gc_count <= WL_GC_COUNT_MAX)
```

```
 7: return;
```

```
 8:  
```

```
 9: now = ktime_get();
```

```
 10: list_for_each_entry_safe_reverse(wl, aux, &wakelocks_lru_list, lru) {
```

```
 11: u64 idle_time_ns;
```

```
 12: bool active;
```

```
 13:  
```

```
 14: spin_lock_irq(&wl->ws.lock);
```

```
 15: idle_time_ns = ktime_to_ns(ktime_sub(now, wl->ws.last_time));
```

```
 16: active = wl->ws.active;
```

```
 17: spin_unlock_irq(&wl->ws.lock);
```

```
 18:  
```

```
 19: if (idle_time_ns < ((u64)WL_GC_TIME_SEC * NSEC_PER_SEC))
```

```
 20: break;
```

```
 21:  
```

```
 22: if (!active) {
```

```
 23: wakeup_source_remove(&wl->ws);
```

```
 24: rb_erase(&wl->node, &wakelocks_tree);
```

```
 25: list_del(&wl->lru);
```

```
 26: kfree(wl->name);
```

```
 27: kfree(wl);
```

```
 28: decrement_wakelocks_number();
```

```
 29: }
```

```
 30: }
```

```
 31: wakelocks_gc_count = 0;
```

```
 32: }
```

> 1）如果当前wakelocks的数目小于最大值（由WL\_GC\_COUNT\_MAX配置，当前代码为100），不回收，直接返回。
>
> 2）否则，从wakelocks\_lru\_most\_recent的尾部（最不活跃的），依次取出wakelock，判断它的idle时间（通过wakeup source lst\_time和当前时间计算）是否超出预设值（由WL\_GC\_TIME\_SEC指定，当前为300s，好长），如果超出且处于deactive状态，调用wakeup\_source\_remove，注销wakeup source，同时把它从红黑树、GC list中去掉，并释放memory资源。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/wakelocks.html)。*
