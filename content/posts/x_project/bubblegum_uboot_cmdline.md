---
title: "X-008-UBOOT-支持命令行(Bubblegum-96平台)"
date: 2016-07-27T21:41:16+08:00
url: "/x_project/bubblegum_uboot_cmdline.html"
gid: "320"
emlog_type: "blog"
summary: "经过前面文章的铺垫，u-boot command \r\nline的支持已经成了一个顺理成章的事情了。因此，本文没有太多技术细节，仅仅记录支持命令行的实现过程，权当“X Project” “【任务2】启动到u-boot command \r\nline”的一个完结。"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["u-boot", "cmdline"]
views: 14403
comment_count: 11
aliases:
  - "/x_project/320.html"
  - "/320.html"
---

#### 1. 前言

经过前面文章的铺垫，u-boot command line的支持已经成了一个顺理成章的事情了。因此，本文没有太多技术细节，仅仅记录支持命令行的实现过程，权当“[X Project](/forum/)” “[【任务2】启动到u-boot command line](/forum/28.html)”的一个完结。

#### 2. 支持命令行的过程

由“[X-007-UBOOT-DDR的初始化(Bubblegum-96平台)](/x_project/bubblegum_uboot_ddr.html)”的描述可知，我们已经成功初始化DDR，并将u-boot放到DDR中执行，基于该成果，我们进一步调试命令行功能。

##### 2.1 修改版型的配置头文件，将u-boot的DEBUG功能打开，以便得到更多的打印信息

> pengo@ubuntu:~/work/xprj/u-boot$ git diff   
> diff --git a/include/configs/bubblegum.h b/include/configs/bubblegum.h   
> index 6ee4227..5f22528 100644   
> --- a/include/configs/bubblegum.h   
> +++ b/include/configs/bubblegum.h   
> @@ -10,7 +10,7 @@   
> #ifndef \_\_BUBBLEGUM\_H   
> #define \_\_BUBBLEGUM\_H   
>   
> -#define DEBUGX   
> +#define DEBUG

##### 2.2 根据“[X-007-UBOOT-DDR的初始化(Bubblegum-96平台)](/x_project/bubblegum_uboot_ddr.html)”所提示的步骤，运行u-boot，得到如下的错误信息。

> initcall: 0000000011003180   
> U-Boot code: 11000000 -> 11014E30 BSS: -> 11014F38   
> initcall: 0000000011002fc8   
> initcall: 000000001100321c   
> DRAM: initcall: 0000000011002834   
> dram\_init   
> dram\_init OK   
> initcall: 0000000011003484   
> Monitor len: 00014F38   
> Ram size: FFFFFFFF80000000   
> Ram top: FFFFFFFF80000000   
> initcall: 0000000011002ff8   
> initcall: 00000000110031b4   
> TLB table from ffffffff7fff0000 to ffffffff7fff6000   
> initcall: 000000001100300c   
> initcall: 0000000011003130   
> Reserving 83k for U-Boot at: ffffffff7ffdb000   
> initcall: 00000000110030fc   
> Reserving 24k for malloc() at: ffffffff7ffd5000   
> initcall: 0000000011003354   
> "Synchronous Abort" handler, esr 0x96000040   
> ELR: 1100b684   
> LR: 11003384   
> x0 : ffffffff7ffd4f68 x1 : 0000000000000000   
> x2 : 0000000000000098 x3 : 0000000000000000   
> x4 : 0000000000000000 x5 : 0000000000000098   
> x6 : 0000000000000000 x7 : 0000000000000004   
> x8 : 0000000000000031 x9 : 0000000000000000   
> x10: 000000000000000f x11: 000000000007f468   
> x12: 000000001100d0d8 x13: 000000000000003c   
> x14: 0000000000000001 x15: 0000000000000008   
> x16: 0000000000000008 x17: 0000000000000000   
> x18: 000000000007f990 x19: 0000000011011c70   
> x20: 0000000011011ba0 x21: 0000000000000000   
> x22: 0000000011011286 x23: 000000001101185b   
> x24: 0000000011011293 x25: 0000000080000000   
> x26: 0000000000000010 x27: 0000002000000000   
> x28: 000000000000000c x29: 000000000007f930   
> Resetting CPU ...   
> resetting ...

##### 2.3 分析错误信息

由上面黄色位置的信息可以推测，应该是reserve\_malloc后面的那个init call出问题了，查一下代码：

> #ifndef CONFIG\_SPL\_BUILD   
> reserve\_malloc,   
> reserve\_board,   
> #endif

reserve\_malloc后面的函数是reserve\_board：

> /\* (permanently) allocate a Board Info struct \*/   
> static int reserve\_board(void)   
> {   
> if (!gd->bd) {   
> gd->start\_addr\_sp -= sizeof(bd\_t);   
> gd->bd = (bd\_t \*)map\_sysmem(gd->start\_addr\_sp, sizeof(bd\_t));   
> memset(gd->bd, '\0', sizeof(bd\_t));   
> debug("Reserving %zu Bytes for Board Info at: %08lx\n",   
> sizeof(bd\_t), gd->start\_addr\_sp);   
> }   
> return 0;   
> }

start\_addr\_sp不对？再看一下上面的日志输出：

> Ram size: FFFFFFFF80000000   
> Ram top: FFFFFFFF80000000

RAM size不对？回忆一下编译过程，有个编译错误：

> /home/pengo/work/xprj/u-boot/board/actions/bubblegum/board.c:136:33: warning: integer overflow in expression [-Woverflow]

代码136行对ram\_size的赋值如下：

> gd->ram\_size = 2 \* 1024 \* 1024 \* 1024; /\* 2GB, TODO \*/

会溢出？先不纠结，先把这个问题修复再说。

##### 2.4 修改ram\_size的赋值，避免溢出

> diff --git a/board/actions/bubblegum/board.c b/board/actions/bubblegum/board.c   
> index 81472a4..ea6fddc 100755   
> --- a/board/actions/bubblegum/board.c   
> +++ b/board/actions/bubblegum/board.c   
> @@ -133,7 +133,7 @@ int dram\_init(void)   
>   
> /\* no need do dram init in here, we have done it in SPL \*/   
>   
> - gd->ram\_size = 2 \* 1024 \* 1024 \* 1024; /\* 2GB, TODO \*/   
> + gd->ram\_size = CONFIG\_SYS\_SDRAM\_SIZE;  
>   
> printf("dram\_init OK\n");   
> return 0;
>
> diff --git a/include/configs/bubblegum.h b/include/configs/bubblegum.h   
>   
> /\*   
> \* u-boot SPL definitions, which is resided in SRAM   
> @@ -33,6 +33,8 @@   
> #define CONFIG\_SYS\_SDRAM\_BASE 0x0   
> #define CONFIG\_NR\_DRAM\_BANKS 1   
>   
> +#define CONFIG\_SYS\_SDRAM\_SIZE 0x3FFFFFFF   
> +

暂时使用一个安全的值，后面再完善。编译重新运行后，出现如下的输出：

> …   
> Initial value for argc=3   
> Final value for argc=3   
> initcall: 00000000110024c4 (relocated to 000000003ffdd4c4)   
> initcall: 00000000110035d0 (relocated to 000000003ffde5d0)   
> initcall: 00000000110035c0 (relocated to 000000003ffde5c0)   
> fdtdec\_get\_config\_string: bootcmd   
> fdtdec\_get\_config\_int: bootsecure   
> ## U-Boot command line is disabled. Please enable CONFIG\_CMDLINE   
> No CLI available   
> resetting ...

OK，一切正常了，只不过由于没有定义CONFIG\_CMDLINE，无法进入命令行。打开相应的配置即可。

##### 2.5 配置命令行功能

配置u-boot，开启命令行有关的配置项包括：

> Command line interface --->   
> [\*] Support U-Boot commands   
> ([xprj]# ) Shell prompt   
> Info commands --->   
> [\*] bdinfo   
> [\*] coninfo

修改后的配置文件为：

> pengo@ubuntu:~/work/xprj/u-boot$ git diff configs/bubblegum\_defconfig   
> diff --git a/configs/bubblegum\_defconfig b/configs/bubblegum\_defconfig   
> index 85a488d..bc0c5f7 100644   
> --- a/configs/bubblegum\_defconfig   
> +++ b/configs/bubblegum\_defconfig   
> @@ -198,8 +198,9 @@ CONFIG\_BOOTSTAGE\_STASH\_SIZE=4096   
> #   
> # Command line interface   
> #   
> -# CONFIG\_CMDLINE is not set   
> -CONFIG\_SYS\_PROMPT="=> "   
> +CONFIG\_CMDLINE=y  
> +# CONFIG\_HUSH\_PARSER is not set   
> +CONFIG\_SYS\_PROMPT="[xprj]# "  
>   
> #   
> # Autoboot options   
> @@ -213,8 +214,8 @@ CONFIG\_SYS\_PROMPT="=> "   
> #   
> # Info commands   
> #   
> -# CONFIG\_CMD\_BDI is not set   
> -# CONFIG\_CMD\_CONSOLE is not set   
> +CONFIG\_CMD\_BDI=y   
> +CONFIG\_CMD\_CONSOLE=y  
> # CONFIG\_CMD\_CPU is not set   
> # CONFIG\_CMD\_LICENSE is not set

再次编译并运行u-boot，OK了，如下：

> [xprj]# help   
> ? - alias for 'help'   
> bdinfo - print Board Info structure   
> coninfo - print console devices and information   
> dm - Driver model low level access   
> env - environment handling commands   
> help - print command description/usage   
> printenv- print environment variables   
> reset - Perform RESET of the CPU   
> setenv - set environment variables   
> version - print monitor, compiler and linker version
>
> [xprj]# bdinfo   
> arch\_number = 0x00000000   
> boot\_params = 0x00000000   
> DRAM bank = 0x00000000   
> -> start = 0x00000000   
> -> size = 0x3FFFFFFF   
> baudrate = 115200 bps   
> TLB addr = 0x3FFF0000   
> relocaddr = 0x3FFD8000   
> reloc off = 0x2EFD8000   
> irq\_sp = 0x3FFD0BD0   
> sp start = 0x3FFD0BD0

以上改动，可参考如下patch：

> [https://github.com/wowotechX/u-boot/commit/7cc2bd4716bb095925eb6e2c3e43cef157cf40d4](https://github.com/wowotechX/u-boot/commit/7cc2bd4716bb095925eb6e2c3e43cef157cf40d4 "https://github.com/wowotechX/u-boot/commit/7cc2bd4716bb095925eb6e2c3e43cef157cf40d4")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_cmdline.html)。
