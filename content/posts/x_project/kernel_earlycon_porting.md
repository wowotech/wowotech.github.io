---
title: "X-012-KERNEL-serial early console的移植"
date: 2016-10-02T22:50:51+08:00
url: "/x_project/kernel_earlycon_porting.html"
gid: "339"
emlog_type: "blog"
summary: "对Linux kernel工程师来说，最依赖的工具非printk莫属（不多解释，大家都懂）。因此，在Linux kernel移植的初期阶段，如果能够尽快地实现printk功能，将会为后续的工作带来极大的帮助。 在众多可用作printk输出的终端里面（串口、屏幕、USB、网络、等等），串口终端（也即串口驱动）无疑是实现起来最简单一种，因此也是嵌入式linux开发过程中（特别是早期阶段）最普遍使用的。"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "Kernel", "console", "earlycon", "printk"]
views: 16813
comment_count: 26
aliases:
  - "/x_project/339.html"
  - "/339.html"
---

## 1. 前言

对Linux kernel工程师来说，最依赖的工具非printk莫属（不多解释，大家都懂）。因此，在Linux kernel移植的初期阶段，如果能够尽快地实现printk功能，将会为后续的工作带来极大的帮助。

在众多可用作printk输出的终端里面（串口、屏幕、USB、网络、等等），串口终端（也即串口驱动）无疑是实现起来最简单一种，因此也是嵌入式linux开发过程中（特别是早期阶段）最普遍使用的。

但是，受限于Linux TTY框架的复杂性[1]，长久以来，在Kernel移植的初期阶段（各种功能都不ready，缺乏有效的调试手段），快速的实现serial driver也是一个不小的挑战。不过，随着serial subsystem中的early console功能的出现，这种状况得到了极大的改善。

本文将借助“[X Project](/forum/)” kernel的开发过程，介绍serial early console功能的移植过程。

注1：博客中“Linux [TTY子系统](/sort/tty_framework)”的分析正在缓慢推进，不过还未涉及console、serial subsystem、earlycon等模块。因此我一直在纠结先写理论（分析），还是先写实践（移植说明）。结论是先写本文，理由是：虽然earlycon功能涉及到TTY子系统的复杂知识，如console driver、tty driver、serial driver等等，但从移植的角度看，我们可以什么都不懂。这种优雅的抽象和封装，是优秀软件（如Linux kernel）所必需具备的特性，也是我们软件人需要竭力追求的神圣目标。

## 2. 移植步骤

#### 2.1 串口驱动

early console是linux serial subsystem的一个子功能，因此需要依附于具体平台的serial driver之下（放心，本文不涉及任何串口驱动的知识）。以“[X Project](/forum/)” 所使用的bubblegum-96平台为例，我们需要在“drivers/tty/serial/”下新建一个serial driver，并修改kernel serial subsystem的Kconfig和Makefile文件，将其添加到kernel的编译系统中， 步骤如下：

1）新建serial driver

> touch drivers/tty/serial/owl-serial.c

其中“owl”是bubblegum-96平台所使用SOC的代号，大家可以根据实际情况，使用和自己平台匹配的名称。

2）修改drivers/tty/serial/Kconfig和drivers/tty/serial/Makefile，将新建的serial driver加入到编译框架中

> diff --git a/drivers/tty/serial/Kconfig b/drivers/tty/serial/Kconfig   
> index 13d4ed6..bbf4b69 100644   
> --- a/drivers/tty/serial/Kconfig   
> +++ b/drivers/tty/serial/Kconfig   
> @@ -1624,6 +1624,14 @@ config SERIAL\_MVEBU\_CONSOLE   
> and warnings and which allows logins in single user mode)   
> Otherwise, say 'N'.
>
> +config SERIAL\_OWL   
> + tristate "Actions OWL serial port support"   
> + depends on ARCH\_OWL   
> + select SERIAL\_CORE   
> + select SERIAL\_CORE\_CONSOLE   
> + help   
> + If you have a machine based on an Actions OWL CPU you   
> + can enable its onboard serial ports by enabling this option.  
> endmenu
>
> config SERIAL\_MCTRL\_GPIO   
> diff --git a/drivers/tty/serial/Makefile b/drivers/tty/serial/Makefile   
> index 8c261ad..3f75d73 100644   
> --- a/drivers/tty/serial/Makefile   
> +++ b/drivers/tty/serial/Makefile   
> @@ -91,6 +91,7 @@ obj-$(CONFIG\_SERIAL\_MEN\_Z135) += men\_z135\_uart.o   
> obj-$(CONFIG\_SERIAL\_SPRD) += sprd\_serial.o   
> obj-$(CONFIG\_SERIAL\_STM32) += stm32-usart.o   
> obj-$(CONFIG\_SERIAL\_MVEBU\_UART) += mvebu-uart.o   
> +obj-$(CONFIG\_SERIAL\_OWL) += owl-serial.o

我们为新建的serial driver指定了“SERIAL\_OWL”配置项，该配置项依赖ARCH\_OWL[2]。与此同时，我们需要选中“SERIAL\_CORE”和“SERIAL\_CORE\_CONSOLE”两个配置项，以支持earlycon功能。

3）配置kernel，开启TTY、serial等功能，并使能我们新加入的serial driver

> cd ~/work/xprj/build   
> make kernel-config
>
> #选中如下的配置项   
> Device Drivers --->   
> Character devices --->   
> [\*] Enable TTY   
> Serial drivers --->   
> [\*] Actions OWL serial port support

完成后make kernel重新编译即可。

#### 2.2 early console的移植

实现early console的移植过程非常简单，包括：

1）实现一个early console的setup接口，并调用serial core提供的注册接口（EARLYCON\_DECLARE）将其注册到kernel中，如下：

> int \_\_init earlycon\_owl\_setup(struct earlycon\_device \*device, const char \*opt)   
> {   
> /\* TODO \*/   
> uart5\_base = early\_ioremap(UART5\_BASE, 4);
>
> device->con->write = earlycon\_owl\_write;   
> return 0;   
> }   
> EARLYCON\_DECLARE(owl\_serial, earlycon\_owl\_setup);

其中“owl\_serial”是early console的名称，earlycon\_owl\_setup是开始使用之前的初始化接口，需要在这个初始化接口中做两件事情：

> 进行一些必要的初始化，如例子中的寄存器map；
>
> 为printk输出制定一个write接口----earlycon\_owl\_write。

注2：“EARLYCON\_DECLARE”是实现early console的一种方法，另外我们也可以使用device tree的方式，为了不增加复杂度，本文就不提及相关的实现了。

注3：为了简单，early console和u-boot[3]使用相同的串口，并且使用相同的配置，因此不需要额外的初始化操作。

注4：虽然配置不变，我们还是需要访问串口寄存器输出字符串，因此需要map相应的IO地址，由于early console需要在很早的时候使用，此时mm还没有初始化，因此我们可以用early\_ioremap[4]进行map。

2）earlycon\_owl\_write的实现

console输出需要字符串处理，可以借用serial core的标准接口----uart\_console\_write：

> static void earlycon\_owl\_write(struct console \*con, const char \*s, unsigned n)   
> {   
> /\* TODO \*/   
> uart\_console\_write(NULL, s, n, owl\_serial\_putc);   
> }

我们需要做的就是提供一个字符输出的API----owl\_serial\_putc，具体可参考代码以及“[X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)[3]”中有关的描述。

3）移植完成后重新编译kernel即可

## 3. 使用说明

移植完成后，可以通过kernel的命令行参数，告诉kernel在启动的时候使用该early console，参数的格式如下：

> earlycon=owl\_serial

其中“earlycon”是关键字，“owl\_serial”是early console的名字。

命令行参数可以通过u-boot传入，为了测试方便，可以暂时加到kernel的配置项中[5]，如下：

> #   
> # Boot options   
> #   
> -CONFIG\_CMDLINE=""   
> +CONFIG\_CMDLINE="earlycon=owl\_serial"

以上改动具体可参考下面的patch：

> [https://github.com/wowotechX/linux/commit/1285ab5e6e5c5bb263a1d715fe04cca2d217bd98](https://github.com/wowotechX/linux/commit/1285ab5e6e5c5bb263a1d715fe04cca2d217bd98 "https://github.com/wowotechX/linux/commit/1285ab5e6e5c5bb263a1d715fe04cca2d217bd98")

## 4. 测试和调试

移植完成后，按照“README.bubblegum96[6]”中的步骤，编译并运行kernel，发现printk信息没有如约出现，没关系，兵来将挡，水来土掩，开始调试了。

#### 4.1 使用点LED的方式，定位问题所在位置

该方法在u-boot移植的初期，也是用过，应该是轻车熟路了[7]。不过在kernel中有点稍微的不一样，我们需要将GPIO有关的寄存器map成虚拟地址才能使用，代码如下（只为暂时调试使用，因而没有上传到代码仓库）：

1）在init/main.c中添加LED debug有关的函数

> +void \_\_init xprj\_earlyyyy\_debug(void)   
> +{   
> + static void \_\_iomem \*gpioa\_outen = NULL;   
> + static void \_\_iomem \*gpioa\_outdat = NULL;   
> +   
> + if (gpioa\_outen == NULL) {   
> + gpioa\_outen = early\_ioremap(0xe01b0000, 4);   
> + gpioa\_outdat = early\_ioremap(0xe01b0008, 4);   
> + }   
> +   
> + writel(0xffffffff, gpioa\_outen);   
> + writel(0xffffffff, gpioa\_outdat);   
> +}

注5：为了可以尽早（在kernel内存管理模块初始化之前）使用，我们使用early\_ioremap获取寄存器的虚拟地址[4]。

注6：为了简单，这里粗暴的把GPIOA的所有GPIO都输出高电平了。

2）根据earlycon的初始化逻辑，在earlycon初始化的路径上，调用debug API，点亮LED。第一个地方是setup\_earlycon（earlycon的具体流程，会在下一篇文章中分析）：

> +extern void \_\_init xprj\_earlyyyy\_debug(void);   
> int \_\_init setup\_earlycon(char \*buf)   
> {   
> const struct earlycon\_id \*match;   
> +#if 1   
> + xprj\_earlyyyy\_debug();   
> + while (1);   
> +#endif  
> +

无法点亮！

接着往前跟踪，放到param\_setup\_earlycon中：

> @@ -204,6 +210,11 @@ static int \_\_init param\_setup\_earlycon(char \*buf)
>
> {   
> int err;   
> +#if 1   
> + xprj\_earlyyyy\_debug();   
> + while (1);   
> +#endif  
> +

还是无法点亮！

怀疑earlycon的代码压根没有执行，检查drivers/tty/serial/Makefile，发现由CONFIG\_SERIAL\_EARLYCON控制：

> obj-$(CONFIG\_SERIAL\_EARLYCON) += earlycon.o

仿照drivers/tty/serial/Kconfig中其它serial driver，在OWL\_SERIAL中select该配置项，如下：

> @@ -1629,6 +1629,7 @@ config SERIAL\_OWL   
> depends on ARCH\_OWL   
> select SERIAL\_CORE   
> select SERIAL\_CORE\_CONSOLE   
> + select SERIAL\_EARLYCON  
> help   
> If you have a machine based on an Actions OWL CPU you   
> can enable its onboard serial ports by enabling this option.

配置kernel后，再次编译测试，得到如下的执行过程：

> param\_setup\_earlycon OK   
> setup\_earlycon OK   
> earlycon\_owl\_setup OK   
> earlycon\_owl\_write FAIL

看来初始化OK了，没有人调用console的write接口？

注7：上面debug的过程中，下面的代码会导致编译错误：

> extern void \_\_init xprj\_earlyyyy\_debug(void);   
> static void earlycon\_owl\_write(struct console \*con, const char \*s, unsigned n)   
> {   
> #if 1   
> xprj\_earlyyyy\_debug();   
> while (1);   
> #endif

错误信息为：

> WARNING: modpost: Found 2 section mismatch(es).   
> To see full details build your kernel with:   
> make CONFIG\_DEBUG\_SECTION\_MISMATCH=y'   
> FATAL: modpost: Section mismatches detected.   
> Set CONFIG\_SECTION\_MISMATCH\_WARN\_ONLY=y to allow them.   
> make[3]: \*\*\* [vmlinux.o] Error 1   
> make[2]: \*\*\* [vmlinux] Error 2

原因是我们在非\_\_init的section中（earlycon\_owl\_write）调用了\_\_init section（xprj\_earlyyyy\_debug）的代码，按照提示说的，打开CONFIG\_SECTION\_MISMATCH\_WARN\_ONLY配置项即可编译通过：

> Kernel hacking --->   
> Compile-time checks and compiler options --->   
> [\*] Make section mismatch errors non-fatal

#### 4.2 使能printk的配置项

依稀记得linux kernel的printk有配置项可以控制使能与否，检查kernel的相关代码，果然如此。重新配置kernel使能该配置项：

> General setup --->   
> [\*] Enable support for printk

再次运行，串口有输出了：

> Starting kernel ...   
> flushing dcache successfully.   
> Booting Linux on physical CPU 0xrFailed to find device node for bpDBPDentry cacInode-cache hash table entries: software IO TLB [mem 0x79cb4000-Memory: 1993624K/2097152K availa0ffSsaK

觉得奇奇怪怪的？没有换行？没有格式化输出？

#### 4.3 检查earlycon驱动

再仔细检查一下drivers/tty/serial/owl-serial.c中owl\_serial\_putc的实现，有个地方写错了（从u-boot抄过来的时候大意了），修改一下：

> static void owl\_serial\_putc(struct uart\_port \*port, int ch)   
> {   
> - if (readl(uart5\_base + UART\_STAT) & UART\_STAT\_TFFU)   
> - return;   
> + /\* wait for TX FIFO untill it is not full \*/   
> + while (readl(uart5\_base + UART\_STAT) & UART\_STAT\_TFFU)   
> + ;   
> writel(ch, uart5\_base + UART\_TXDAT);   
> }

终于OKAY了：

> Booting Linux on physical CPU 0x0   
> Linux version 4.6.0-rc5+ (pengo@ubuntu) (gcc version 4.8.3 20131202 (prerelease) (crosstool-NG linaro-1.13.1-4.8-2013.12 - Linaro GCC 2013.11) ) #8 SMP Mon Oct 3 23:36:39 PDT 2016   
> Boot CPU: AArch64 Processor [410fd032]   
> earlycon: owl\_serial0 at I/O port 0x0 (options '')   
> bootconsole [owl\_serial0] enabled   
> Failed to find device node for boot cpu   
> missing boot CPU MPIDR, not enabling secondaries   
> percpu: Embedded 14 pages/cpu @ffffffc07ffdd000 s28032 r0 d29312 u57344   
> Detected VIPT I-cache on CPU0   
> Built 1 zonelists in Zone order, mobility grouping on. Total pages: 516096   
> Kernel command line: earlycon=owl\_serial   
> PID hash table entries: 4096 (order: 3, 32768 bytes)   
> Dentry cache hash table entries: 262144 (order: 9, 2097152 bytes)   
> Inode-cache hash table entries: 131072 (order: 8, 1048576 bytes)   
> software IO TLB [mem 0x79cb4000-0x7dcb4000] (64MB) mapped at [ffffffc079cb4000-ffffffc07dcb3fff]   
> Memory: 1993624K/2097152K available (1028K kernel code, 78K rwdata, 120K rodata, 116K init,   
> 201K bss, 103528K reserved, 0K cma-reserved)   
> Virtual kernel memory layout:   
> modules : 0xffffff8000000000 - 0xffffff8008000000 ( 128 MB)   
> vmalloc : 0xffffff8008000000 - 0xffffffbdbfff0000 ( 246 GB)   
> .text : 0xffffff8008080000 - 0xffffff8008181000 ( 1028 KB)   
> .rodata : 0xffffff8008181000 - 0xffffff80081a0000 ( 124 KB)   
> .init : 0xffffff80081a0000 - 0xffffff80081bd000 ( 116 KB)   
> .data : 0xffffff80081bd000 - 0xffffff80081d0800 ( 78 KB)   
> fixed : 0xffffffbffe7fd000 - 0xffffffbffec00000 ( 4108 KB)   
> PCI I/O : 0xffffffbffee00000 - 0xffffffbfffe00000 ( 16 MB)   
> memory : 0xffffffc000000000 - 0xffffffc080000000 ( 2048 MB)   
> SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=1, Nodes=1   
> Hierarchical RCU implementation.   
> Build-time adjustment of leaf fanout to 64.   
> RCU restricting CPUs from NR\_CPUS=64 to nr\_cpu\_ids=1.   
> RCU: Adjusting geometry for rcu\_fanout\_leaf=64, nr\_cpu\_ids=1   
> NR\_IRQS:64 nr\_irqs:64 0   
> Kernel panic - not syncing: No interrupt controller found.   
> ---[ end Kernel panic - not syncing: No interrupt controller found.

终于从蛮荒地世界中走出来了，庆祝吧~~！！

注8：上述过程可参考如下patch：

> [https://github.com/wowotechX/linux/commit/1e18b4d2a5df61e5f495dbc071fe2ad2740d7061](https://github.com/wowotechX/linux/commit/1e18b4d2a5df61e5f495dbc071fe2ad2740d7061 "https://github.com/wowotechX/linux/commit/1e18b4d2a5df61e5f495dbc071fe2ad2740d7061")

## 5. 参考文档

[1] [Linux TTY framework(2)\_软件架构](/tty_framework/tty_architecture.html)

[2] [X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台)](/x_project/bubblegum_kernel_porting.html)

[3] [X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)

[4] [Fix-Mapped Addresses](/memory_management/fixmap.html)

[5] [Linux kernel内核配置解析(5)\_Boot options(基于ARM64架构)](/linux_kenrel/kernel_config_boot_option.html)

[6] README.bubblegum96，[https://github.com/wowotechX/doc/blob/master/README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96 "https://github.com/wowotechX/doc/blob/master/README.bubblegum96")

[7] [通过点亮LED的方法调试嵌入式代码](/soft/debug_using_led.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/kernel_earlycon_porting.html)。
