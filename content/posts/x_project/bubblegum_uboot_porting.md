---
title: "X-003-UBOOT-基于Bubblegum-96平台的u-boot移植说明"
date: 2016-05-29T18:00:10+08:00
url: "/x_project/bubblegum_uboot_porting.html"
gid: "304"
emlog_type: "blog"
summary: "本文是X Project “ 【任务1】启动过程-Boot from USB ”的一部分，将以“Bubblegum 96boards”为例，介绍将u-boot移植到一个新的平台上的步骤和方法，并以此为契机，分析、理解u-boot的编译过程。"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["bubblegum", "uboot", "porting"]
views: 26300
comment_count: 42
aliases:
  - "/x_project/304.html"
  - "/304.html"
---

#### 1. 前言

本文是X Project “[【任务1】启动过程-Boot from USB](/forum/15.html)”的一部分，将以“Bubblegum 96boards”为例，介绍将u-boot移植到一个新的平台上的步骤和方法，并以此为契机，分析、理解u-boot的编译过程。

#### 2. 思路

由“[u-boot启动流程分析(1)\_平台相关部分](/u-boot/boot_flow_1.html)”的介绍可知，u-boot平台相关的代码，是以“board—>machine—>arch—>cpu”为框架逐层抽象出来的。因此，u-boot的移植，也要遵循这个框架，逐层进行，包括：

> 层次1，ARCH有关的代码移植（如ARM）；
>
> 层次2，CPU有关的代码移植（如armv8）；
>
> 层次3，Machine有关的代码移植（如S900）；
>
> 层次4，Board有关的代码移植（如Bubblegum 96boards）。

而移植的过程，需要遵守如下的基本原则：

> 如果目标平台所对应的ARCH，已经被u-boot upstream代码支持，则直接从层次2（CPU移植）开始；
>
> 如果目标平台所使用的CPU，已经被u-boot upstream代码支持，则直接从层次3（Machine移植）开始；
>
> 如果目标平台所使用的Machine，已经被u-boot upstream代码支持，则直接从层次4（Board移植）开始；
>
> 如果目标平台所使用的Board，已经被u-boot upstream代码支持，则移植工作已经完成了。

对“Bubblegum 96boards”来说，upstream代码已经支持了ARCH（ARM）和CPU（armv8），因此我们将从层次3 Machine移植开始。

最后，为了简单，本文的移植工作，和“[【任务1】启动过程-Boot from USB](/forum/15.html)”所设定的目标一致，即Board有关的代码被执行后，点亮一个LED灯即可。

注1：本文的移植工作，将以u-boot SPL功能为主，因此相关的分析过程（如编译脚本等），主要以SPL为例，而具体的u-boot部分，大家可以触类旁通。

#### 3. 准备工作

##### 3.1 编译环境

1）运行linux系统的PC（大家自行准备，这里以Ubuntu为例）。

2）安装必要的库：

> sudo apt-get install ncurses-dev

##### 3.2 工具和代码下载

移植开始前，我们需要下载u-boot代码、交叉编译工具等。如下：

> mkdir x\_project
>
> cd x\_project
>
> git clone [git@github.com:wowotechX/u-boot.git](mailto:git@github.com:wowotechX/u-boot.git)
>
> git clone [git@github.com:wowotechX/tools.git](mailto:git@github.com:wowotechX/tools.git)
>
> git clone [git@github.com:wowotechX/build.git](mailto:git@github.com:wowotechX/build.git)

注2：tools中有32位、64位等环境下的交叉编译工具。

注3：我们将在build目录中保存一些编译有关的脚本，以方便移植及后续的开发工作。

注4：由于众所周知的原因，我们从github上clone代码的时候，速度奇慢，经过wowo的探索和研究，下面的方法可以改善很多（我只贴出步骤，不再做过多解释，你懂的）。

> 1）%￥#￥……××&（×&
>
> wget <https://raw.githubusercontent.com/racaljk/hosts/master/hosts> -qO /tmp/hosts && sudo sh -c 'cat /tmp/hosts > /etc/hosts'
>
> sudo /etc/init.d/dns-clean start
>
> sudo /etc/init.d/networking restart
>
> 2）使用ssh clone
>
> github ssh配置的方法，可参考“[X-001-PRE-git介绍及操作记录](/x_project/git_record.html)”。

#### 4. 移植过程

注5：为了减少文档的工作量，移植过程尽量以git diff等source code的方式给出，大家可以参考，不再过多语言解释。

##### 4.1 基本符号的定义

本文的目标平台是“Bubblegum-96（<http://www.96boards.org/products/>）“，该平台使用炬芯公司（Actions）的S900 SOC，属于ARMv8架构，按照u-boot “board—>machine—>arch—>cpu”的架构，我们定义如下符号，以指导后续的移植工作：

> Board -> bubblegum   
> Vendor -> actions   
> Machine(SoC) -> s900   
> Arch -> arm   
> CPU -> armv8

##### 4.2 目录结构以及Kconfig的确定

本节将参考“[doc/README.kconfig](https://github.com/wowotechX/u-boot/blob/x_integration/doc/README.kconfig)”文档，进行平台有关的基础框架的移植：

1）在board/目录中创建“actions/bubblegum” 目录，并提供Kconfig和Makefile文件

> vim@vimpc:~/work/x\_project/u-boot$ mkdir -p board/actions/bubblegum
>
> vim@vimpc:~/work/x\_project/u-boot$ touch board/actions/bubblegum/Kconfig
>
> vim@vimpc:~/work/x\_project/u-boot$ touch board/actions/bubblegum/Makefile

2）在arch/arm/Kconfig中，添加“bubblegum-96”的配置菜单

> --- a/arch/arm/Kconfig   
> +++ b/arch/arm/Kconfig   
> @@ -744,6 +744,13 @@ config TARGET\_THUNDERX\_88XX   
> bool "Support ThunderX 88xx"   
> select OF\_CONTROL   
>   
> +config TARGET\_BUBBLEGUM   
> + bool "Support Bubblegum 96Board"   
> + select ARM64   
> + select SUPPORT\_SPL   
> + select SPL   
> + help   
> + Support for Bubblegum 96boards platform based on Actions S900 Soc,   
> + with 4xA53 CPU, PowerVR G6230 GPU, 2GB RAM, and USB 3.0 support.   
> +  
> endchoice   
>   
> source "arch/arm/mach-at91/Kconfig"   
> @@ -881,6 +888,7 @@ source "board/vscom/baltos/Kconfig"   
> source "board/woodburn/Kconfig"   
> source "board/work-microwave/work\_92105/Kconfig"   
> source "board/zipitz2/Kconfig"   
> +source "board/actions/bubblegum/Kconfig"
>
> source "arch/arm/Kconfig.debug"

此处会select ARM64，此时arch、board、CPU等结构已经确定。同时，我们select了SUPPORT\_SPL和SPL两个配置项，表明该版型将会使用SPL功能。

3）根据4.1的符号定义，在board/actions/bubblegum/Kconfig中，添加如下配置项：

> --- a/board/actions/bubblegum/Kconfig   
> +++ b/board/actions/bubblegum/Kconfig   
> @@ -0,0 +1,21 @@   
> +#   
> +# wowo [wowo@wowotech.net](mailto:wowo@wowotech.net)  
> +#   
> +# SPDX-License-Identifier: GPL-2.0+   
> +#   
> +   
> +if TARGET\_BUBBLEGUM   
> +   
> +config SYS\_BOARD   
> + default "bubblegum"   
> +   
> +config SYS\_VENDOR   
> + default "actions"   
> +   
> +config SYS\_SOC   
> + default "s900"   
> +   
> +config SYS\_CONFIG\_NAME   
> + default "bubblegum"   
> +   
> +endif

根据README的描述，定义上述配置项之后，u-boot会编译如下的目录：

> Define CONFIG\_SYS\_CPU="cpu" to compile arch//cpu/   
> arch/arm/cpu/armv8   
>  Q：并没有看到CONFIG\_SYS\_CPU的定义？   
> A：在“arm/Kconfig”中定义，“default "armv8" if ARM64”，这就是为什么在上面Target定义中“select ARM64”的原因。
>
> Define CONFIG\_SYS\_SOC="soc" to compile arch//cpu//   
> arch/arm/cpu/armv8/s900   
> Q：如果该目录不存在，是否还会编译？   
> A：应该不会。
>
> Define CONFIG\_SYS\_VENDOR="vendor" to compile board//common/\* and board///\*   
>  board/actions/common/\*   
> board/actions/bubblegum/\*
>
> Define CONFIG\_SYS\_CONFIG\_NAME="target" to include include/configs/.h   
> include/configs/bubblegum.h

4）创建该板子有关的配置头文件

u-boot的配置有两种方式：一种是autoconf的方式，通过menuconfig生成.config，然后再转换为conf.h，类似于kernel的配置文件；另一种是通过版型有关的头文件（如上面的include/configs/bubblegum.h）。

autoconf的方式，后面再介绍，这里先创建一个头文件：

> [vim@vimpc:~/work/x\_project/u-boot$](mailto:vim@vimpc:~/work/x_project/u-boot$) cat include/configs/bubblegum.h
>
> /\*   
> \* (C) Copyright 2016 wowotech   
> \*   
> \* wowo[wowo@wowotech.net](mailto:wowo@wowotech.net)  
> \*   
> \* Configuration for Bubblegum 96boards.   
> \*   
> \* SPDX-License-Identifier: GPL-2.0+   
> \*/   
> #ifndef \_\_BUBBLEGUM\_H   
> #define \_\_BUBBLEGUM\_H   
>   
> #endif

5）使用menuconfig，生成.config，并保存为bubblegum\_defconfig

> cd ~/work/x\_project/u-boot
>
> make menuconfig

配置Architecture和Target：

> Architecture select (ARM architecture) --->
>
> ARM architecture --->   
> Target select (Support Bubblegum 96Board) --->

关闭Command line interface配置项下面所有的内容：

> Command line interface --->

其它暂时用默认值，保存退出，得到.config文件，然后另存为bubblegum\_defconfig（具体内容可参考“[https://github.com/wowotechX/u-boot/blob/x\_integration/configs/bubblegum\_defconfig](https://github.com/wowotechX/u-boot/blob/x_integration/configs/bubblegum_defconfig "https://github.com/wowotechX/u-boot/blob/x_integration/configs/bubblegum_defconfig")”）：

> cp .config configs/bubblegum\_defconfig

##### 4.3 尝试编译一次

在这之前，现将当前改动提交到本地的u-boot仓库：

> vim@vimpc:~/work/x\_project/u-boot$ git commit -a -m "Basic porting for bubblegum 96board"
>
> [x\_dev 2315343] Basic porting for bubblegum 96board
>
> 5 files changed, 583 insertions(+)
>
> create mode 100644 arch/arm/bubblegum\_defconfig
>
> create mode 100644 board/actions/bubblegum/Kconfig
>
> create mode 100644 board/actions/bubblegum/Makefile
>
> create mode 100644 include/configs/bubblegum.h

然后在x\_project/build目录下，写一个简单的Makefile文件（可参考“[https://github.com/wowotechX/build](https://github.com/wowotechX/build "https://github.com/wowotechX/build")”），进行编译操作：

> make u-boot

肯定会出错，没关系，兵来将挡，水来土掩，根据错误提示，一一解决。

##### 4.4 在“include/configs/bubblegum.h”添加必要的配置项

具体可参考“[https://github.com/wowotechX/u-boot/blob/x\_integration/include/configs/bubblegum.h](https://github.com/wowotechX/u-boot/blob/x_integration/include/configs/bubblegum.h "https://github.com/wowotechX/u-boot/blob/x_integration/include/configs/bubblegum.h")”，对我们此次的任务来说，如下配置项需要如实提供：

> #define CONFIG\_SPL\_TEXT\_BASE 0xe406b200
>
> #define CONFIG\_SPL\_MAX\_SIZE (1024 \* 20)
>
> #define CONFIG\_SPL\_STACK 0xe407f000

CONFIG\_SPL\_TEXT\_BASE是SPL在SRAM中的运行地址，可以根据“[X-002-HW-S900芯片boot from USB有关的硬件描述](/x_project/s900_hw_adfu.html)”中问题4的答案设置。CONFIG\_SPL\_MAX\_SIZE是SPL最大的size（由SRAM可供执行SPL的空间决定），我们这里暂时选为20K。

CONFIG\_SPL\_STACK是SPL的堆栈基址，同样可以根据“[X-002-HW-S900芯片boot from USB有关的硬件描述](/x_project/s900_hw_adfu.html)”中问题4的答案设置。

其它的配置项，此时不需要明白它们的具体意义，纯粹是为了解决编译错误。

添加后，再编译，还会出错，因为board/actions/bubblegum/中还没有C文件，随后加上。

##### 4.5 在“board/actions/bubblegum/”中添加board有关的C文件

具体可参考“[https://github.com/wowotechX/u-boot/tree/x\_integration/board/actions/bubblegum](https://github.com/wowotechX/u-boot/tree/x_integration/board/actions/bubblegum "https://github.com/wowotechX/u-boot/tree/x_integration/board/actions/bubblegum")”中的Makefile和board.c两个文件。

board.c中有一个名称为board\_init\_f函数，由CONFIG\_SPL\_BUILD配置项包住，我们可以在其中添加点LED的代码（具体的GPIO和LED的对应关系，可参考“Bubblegum 96boards原理图[3]”），如下：

> #ifdef CONFIG\_SPL\_BUILD   
> void board\_init\_f(ulong bootflag)   
> {   
> writel(readl(GPIOA\_OUTEN) | (1 << TEST\_LED\_GPIO), GPIOA\_OUTEN);   
> writel(readl(GPIOA\_OUTDAT) | (1 << TEST\_LED\_GPIO), GPIOA\_OUTDAT);
>
> while (1);   
> }
>
> …
>
> #endif

其它变量和函数，纯粹是为了解决编译错误，此时先不要管它们的含义（后面用到的时候再说）。

再尝试一次编译，OK，成功了：

> vim@vimpc:~/work/x\_project/build$ ls out/u-boot/spl/ -l
>
> 总用量 152   
> …   
> -rwxrwxr-x 1 vim vim 107724 5月 28 21:28 u-boot-spl   
> -rwxrwxr-x 1 vim vim 6939 5月 28 21:28 u-boot-spl.bin  
> -rw-rw-r-- 1 vim vim 12540 5月 28 21:28 u-boot-spl.cfg   
> -rw-rw-r-- 1 vim vim 1055 5月 28 21:28 u-boot-spl.lds   
> -rw-rw-r-- 1 vim vim 17416 5月 28 21:28 u-boot-spl.map   
> -rwxrwxr-x 1 vim vim 6939 5月 28 21:28 u-boot-spl-nodtb.bin

按理说，通过DFU工具，把u-boot-spl.bin上传到SRAM的0xe406b200处并执行，LED应该亮了。

#### 5. 总结和思考

##### 5.1 debug手段

本文完成的时候，相关的改动已经上传到github了，具体可参考：

> [https://github.com/wowotechX/u-boot/commit/2f22e86e9b1c23771d59bee19ff364e198cbda40](https://github.com/wowotechX/u-boot/commit/2f22e86e9b1c23771d59bee19ff364e198cbda40 "https://github.com/wowotechX/u-boot/commit/2f22e86e9b1c23771d59bee19ff364e198cbda40")
>
> [https://github.com/wowotechX/build/commit/f01a056c54eb74f5721e9a72291132825a38c395](https://github.com/wowotechX/build/commit/f01a056c54eb74f5721e9a72291132825a38c395 "https://github.com/wowotechX/build/commit/f01a056c54eb74f5721e9a72291132825a38c395")

不过没有实际在板子上运行。由此得出一个疑问：

> 如果代码不能正确work（点亮LED），我们用什么手段debug？是不是除了JTAG别无它法？

还真不好办，暂时从软件逻辑上把握吧，只要能点亮一个灯，后面的事情就好办了。

##### 5.2 为什么没有看到machine相关的代码移植？

这是一个值得思考的问题。我们在“[u-boot启动流程分析(1)\_平台相关部分](/u-boot/boot_flow_1.html)”中命名提到了machine的概念，为什么在移植的时候却被忽略了？

要回答这个问题，我们可以回忆一下linux kernel中device tree的目的，以及ARM64的现状：是的，在arm64中已经把machine的概念去掉了（以往那么mach-xxx的目录不存在了），所有平台相关的代码，都分布在各种的device driver中过了。虽然u-boot没有明确提出这个概念，但是我们也要努力实现这个目标。因此：

> 在X project开发的过程中，我们要尽力避免machine有关的的代码出现。

##### 5.3 链接脚本

我们在“[u-boot启动流程分析(1)\_平台相关部分](/u-boot/boot_flow_1.html)”中有过一个假设，即：

> 本文先不涉及u-boot和平台相关的Kconfig/Makefile部分，以ARM64为例，假定u-boot首先从“arch/arm/cpu/armv8/start.S”的\_start接口开始执行。因此我们从\_start开始分析。

要解释这个假设，我们需要结合上面的移植过程，从u-boot的编译过程入手，进行简单的分析。

**5.3.1 链接脚本简介**

为了方便大家的理解，这里先从\_start接口反推，看一下u-boot编译的链接脚本（本文主要以SPL为例，u-boot类似）：

> /\* arch/arm/cpu/armv8/u-boot-spl.lds \*/
>
> MEMORY { .sram : ORIGIN = CONFIG\_SPL\_TEXT\_BASE,   
> LENGTH = CONFIG\_SPL\_MAX\_SIZE }   
> MEMORY { .sdram : ORIGIN = CONFIG\_SPL\_BSS\_START\_ADDR,   
> LENGTH = CONFIG\_SPL\_BSS\_MAX\_SIZE }   
>   
> OUTPUT\_FORMAT("elf64-littleaarch64", "elf64-littleaarch64", "elf64-littleaarch64")   
> OUTPUT\_ARCH(aarch64)   
> ENTRY(\_start)   
> SECTIONS   
> {   
> .text : {   
> . = ALIGN(8);   
> \*(.\_\_image\_copy\_start)   
> CPUDIR/start.o (.text\*)   
> \*(.text\*)   
> } >.sram   
> ...   
> }

由上面的链接脚本可知，u-boot（这里为SPL，后面不再特意区分）image的开始位置，存放的是“CPUDIR/start.o”，我们应该猜到了，就是“arch/arm/cpu/armv8/start.o”。而start.S第一条指令，就是\_start，所以系统启动后，执行的第一条指令，就是\_start。因此，接下来我们将以此为线索，通过分析u-boot的编译过程，弄清楚如下的问题：

> 1）armv8目录下的链接脚本，是怎么选中并参与到u-boot的编译中的？
>
> 2）“CPUDIR”到底是怎么定义的？

不过在此之前，我们要先解释一下链接脚本开始的那几个宏定义（分析u-boot的是时候，大家一定要对CONFIG\_XXX高度敏感）：

> CONFIG\_SPL\_TEXT\_BASE，定义了u-boot SPL代码段的基地址。换句话说，就是我们希望SPL在哪个地址被执行。再换句话说，就是SPL image被装载到的RAM地址。回忆一下“[X-002-HW-S900芯片boot from USB有关的硬件描述](/x_project/s900_hw_adfu.html)”中的问题4，我们应该将它设定为可以被SPL使用的SRAM地址。
>
> CONFIG\_SPL\_MAX\_SIZE，定义SPL代码段的最大size，这是由运行SPL的SRAM的大下做决定的，我们应该根据实际情况设置。
>
> CONFIG\_SPL\_BSS\_START\_ADDR，定义了SPL BBS段的基地址。由“.sdram”标号可知，SPL的BSS段可以放到SDRAM中。这个特性很有意思，我们后面用到的时候再分析。
>
> CONFIG\_SPL\_BSS\_MAX\_SIZE，定义SPL BSS段的最大size。

因此，我们也就明白了上面4.2小节中bubblegum.h文件中，为什么一定要如实定义这些配置项了。

**5.3.2 链接脚本的指定**

u-boot所有的编译动作，都是从根目录下的Makefile文件开始的，因此，通过阅读该文件，可以获取链接脚本的指定方式。

注6：本文主要以SPL的编译为例，u-boot类似（甚至会更简单）。

1）Makefile

参考Makefile的如下代码（不再详细分析）：

> all: $(ALL-y)   
> ALL-$(CONFIG\_SPL) += spl/u-boot-spl.bin   
> spl/u-boot-spl.bin: spl/u-boot-spl   
> @:   
> spl/u-boot-spl: tools prepare $(if $(CONFIG\_OF\_SEPARATE),dts/dt.dtb)   
> $(Q)$(MAKE) obj=spl -f $(srctree)/scripts/Makefile.spl all

因此，如果定义CONFIG\_SPL，则会编译SPL，直到“$(srctree)/scripts/Makefile.spl”中。

2）Makefile.spl

> /\* scripts/Makefile.spl \*/
>
> # Linker Script   
>   
> ifdef CONFIG\_SPL\_LDSCRIPT   
> # need to strip off double quotes   
> LDSCRIPT := $(addprefix $(srctree)/,$(CONFIG\_SPL\_LDSCRIPT:"%"=%))   
> endif
>
> ifeq ($(wildcard $(LDSCRIPT)),)   
> LDSCRIPT := $(srctree)/board/$(BOARDDIR)/u-boot-spl.lds   
> endif
>
> ifeq ($(wildcard $(LDSCRIPT)),)   
> LDSCRIPT := $(srctree)/$(CPUDIR)/u-boot-spl.lds   
> endif
>
> ifeq ($(wildcard $(LDSCRIPT)),)   
> LDSCRIPT := $(srctree)/arch/$(ARCH)/cpu/u-boot-spl.lds   
> endif
>
> ifeq ($(wildcard $(LDSCRIPT)),)   
> $(error could not find linker script)   
> endif

由此可知，SPL的链接脚本可以通过如下方式指定（越靠前的，优先级越高，也越不通用）：

> 通过CONFIG\_SPL\_LDSCRIPT自定义；
>
> 以board为单位，通过”$(srctree)/board/$(BOARDDIR)/u-boot-spl.lds“指定；
>
> 通过”$(srctree)/$(CPUDIR)/u-boot-spl.lds“指定；
>
> 通过”$(srctree)/arch/$(ARCH)/cpu/u-boot-spl.lds“指定。

结合5.3.1小节ARMv8链接脚本的路径----“arch/arm/cpu/armv8/u-boot-spl.lds”，我们将目光锁定在“CPUDIR”这个变量上。看来殊途同归啊，5.3.1小节提出的第二个问题，也是“CPUDIR”，我们就接着探索吧。

3）CPUDIR

在u-boot根目录的config.mk中，我们可以看到“CPUDIR”的定义，如下：

> CPUDIR=arch/$(ARCH)/cpu$(if $(CPU),/$(CPU),)

好吧，矛盾转移到了“ARCH”和“CPU”两个变量上面了。接着在config.mk中查找，发现这两个家伙的定义如下：

> ARCH := $(CONFIG\_SYS\_ARCH:"%"=%)
>
> CPU := $(CONFIG\_SYS\_CPU:"%"=%)

矛盾接着转移，此时menuconfig可以出场了。u-boot在进行menuconfig的时候，在菜单中，第一个需要确定的配置项，就是Architecture，以ARM为例，如下：

> Architecture select   
> (X) ARM architecture

我们不去细究auto make脚本的执行过程，但需要看一下定义“Architecture选择”的Kconfig文件----arch/Kconfig，如下：

> config ARM   
> bool "ARM architecture"   
>   
> source "arch/arm/Kconfig"

接着看：

> menu "ARM architecture"   
> depends on ARM
>
> config SYS\_ARCH   
> default "arm"
>
> config ARM64   
> bool
>
> config SYS\_CPU   
> ...   
> default "armv8" if ARM64

SYS\_ARCH已经出来了，而SYS\_CPU则依赖于具体的CPU（如ARM64），那么CONFIG\_ARM64在哪里定义呢？参考4.2小节中的介绍即可。

##### 5.4 编译过程

TODO，有时间再介绍吧。

#### 6. 参考文档

[1] S900 IC Spec，<https://github.com/96boards/documentation/blob/master/bubblegum-96/SoC_bubblegum96.pdf>

[2] Bubblegum 96boards硬件手册，<https://github.com/96boards/documentation/blob/master/bubblegum-96/HardwareManual_Bubblegum96.pdf>

[3] Bubblegum 96boards原理图，<https://github.com/96boards/documentation/blob/master/bubblegum-96/bubblegum-96_Schematic_V1.0.pdf>

[4] linaro-adfu-tool，<https://github.com/96boards-bubblegum/linaro-adfu-tool/blob/master/src/linaro-adfu-tool-bg96.c>

[5] [X-002-HW-S900芯片boot from USB有关的硬件描述](/x_project/s900_hw_adfu.html)

[6] [u-boot启动流程分析(1)\_平台相关部分](/u-boot/boot_flow_1.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_porting.html)。
