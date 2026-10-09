---
title: "X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)"
date: 2016-08-24T22:34:47+08:00
url: "/x_project/bubblegum_uboot_booti.html"
gid: "328"
emlog_type: "blog"
summary: "“ X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台) ”中介绍了ARM64平台下，配置、编译、生成Linux kernel Image文件的方法。Image文件生成后，我们可以借助DFU工具将它下载到板子的DRAM中，然后借助u-boot boot有关的命令，加载并运行之（这个过程也称作引导）。 针对不同的Kernel image格式，u-boot提供了不同"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["arm64", "u-boot", "dtb", "bootm", "booti", "Image"]
views: 30270
comment_count: 2
aliases:
  - "/x_project/328.html"
  - "/328.html"
---

#### 1. 前言

“[X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台)](/x_project/bubblegum_kernel_porting.html)”中介绍了ARM64平台下，配置、编译、生成Linux kernel Image文件的方法。Image文件生成后，我们可以借助DFU工具将它下载到板子的DRAM中，然后借助u-boot boot有关的命令，加载并运行之（这个过程也称作引导）。

针对不同的Kernel image格式，u-boot提供了不同的boot指令，例如：

> booti，引导ARM64 kernel image----Image；
>
> bootz，引导ARM kernel image----zImage；
>
> bootm，引导u-boot自定义的kernel image----uImage。

由于u-boot自定义的image格式（uImage），有着强大而又复杂的功能，本文暂时不想涉及，因此我们以booti命令为例，介绍u-boot的引导过程。

#### 2. u-boot booti配置

##### 2.1 bootm和booti

在u-boot中，bootm是一个可以执行位于memory中的应用程序的命令，在[u-boot README](https://github.com/wowotechX/u-boot/blob/x_integration/README)中的介绍如下：

> Boot Linux:   
> -----------
>
> The "bootm" command is used to boot an application that is stored in   
> memory (RAM or Flash). In case of a Linux kernel image, the contents   
> of the "bootargs" environment variable is passed to the kernel as   
> parameters. You can check and modify this variable using the   
> "printenv" and "setenv" commands:

booti是bootm命令的一个子集，可用于执行位于memory中的ARM64 kernel Image，其格式如下：

> booti addr [initrd[:size]] [fdt]

其中：addr是kernel Image文件所在的memory地址；[initrd[:size]]是initrd在memory中的位置和size，可以不指定，使用“-”代替即可；fdt是flat device tree（就是传说中的dtb文件）在memory中的地址，在ARM64中，它是必选的。

##### 2.2 配置u-boot，使其支持booti

首先，使用u-boot的menuconfig，打开bootm的配置项：

> cd ./build   
> make uboot-config
>
> Command line interface --->   
> Boot commands --->   
> [\*] bootm

其次，由于booti命令需要“CONFIG\_CMD\_BOOTI”配置项，而该配置项在u-boot的kconfig架构中没有，因此我们需要在板子的配置头文件中增加，如下：

> diff --git a/include/configs/bubblegum.h b/include/configs/bubblegum.h   
> index f0f00d3..e03fb09 100644   
> --- a/include/configs/bubblegum.h   
> +++ b/include/configs/bubblegum.h   
> @@ -71,4 +71,6 @@   
> #define CONFIG\_BOARD\_EARLY\_INIT\_F   
> +#define CONFIG\_CMD\_BOOTI  
> +   
> #endif

##### 2.3 配置u-boot，使能对FDT library的支持

u-boot在boot ARM64 kernel Image的同时，也需要解析并校验flat device tree文件，然后将其传递给kernel。而这些需要FDT library的支持，如下：

> cd ./build   
> make uboot-config
>
> Library routines --->   
> [\*] Enable the FDT library

##### 2.4 编译并启动u-boot

> cd ./build   
> make uboot
>
> # 参考[doc/README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96)中的介绍，执行u-boot，然后查看是否已经有booti命令

#### 3. 使用booti boot Image文件

参考“[X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台)](/x_project/bubblegum_kernel_porting.html)”中的成果，尝试在u-boot中使用booti命令，加载并执行kernel Image，步骤如下：

1）参考[doc/README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96)中的介绍，下载并运行splboot.bin，初始化Bubblegum-96的DDR。

2）使用dfu工具，将kernel Image下载到DDR中：

> sudo ../tools/dfu/dfu bubblegum 0x80000 out/linux/arch/arm64/boot/Image 0 #do not execute it

注1：DDR的起始地址为0x0，根据“[X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台)](/x_project/bubblegum_kernel_porting.html)”中的介绍，我们需要把Image文件加载到0x80000处。

3）使用dfu工具，将kernel dtb文件下载到DDR中：

> sudo ../tools/dfu/dfu bubblegum 0x1000000 out/linux/arch/arm64/boot/dts/actions/s900-bubblegum.dtb 0 #do not execute it

注2：我们将dtb文件放置到kernel Image之后16MB（0x1000000）的位置处。在kernel Image不大于16MB的情况下，不会覆盖kernel，否则需要加大该地址。

4）使用dfu工具，下载并执行u-boot：

> sudo ../tools/dfu/dfu bubblegum 0x11000000 out/u-boot/u-boot-dtb.bin 1

注3：我们的u-boot位于272MB左右的位置，互不干涉。

5）boot kernel

执行booti命令，boot kernel（三个参数依次是kernel地址、initrd、dtb地址）：

> booti 0x80000 - 0x1000000

执行结果如下：

> [xprj]# booti 0x80000 - 0x1000000   
> ## Current stack ends at 0x3ffbc4f0 \* kernel: cmdline image address = 0x00080000   
> ## Skipping init Ramdisk   
> ## No init Ramdisk   
> ramdisk start = 0x00000000, ramdisk end = 0x00000000   
> \* fdt: cmdline image address = 0x01000000   
> ## Checking for 'FDT'/'FDT Image' at 01000000   
> Wrong FIT format: no description   
> \* fdt: raw FDT blob   
> ## Flattened Device Tree blob at 01000000   
> Booting using the fdt blob at 0x1000000   
> of\_flat\_tree at 0x01000000 size 0x000000a9   
> Initial value for argc=3   
> Final value for argc=3   
> ## FIT configuration was not specified   
> using: FDT   
> ## initrd\_high = 0x3fffffff, copy\_to\_ram = 1   
> ramdisk load start = 0x00000000, ramdisk load end = 0x00000000   
> ## device tree at 0000000001000000 ... 00000000010000a8 (len=12457 [0x30A9])   
> Loading Device Tree to 000000003ffb8000, end 000000003ffbb0a8 ... OK   
> Initial value for argc=3   
> Final value for argc=3   
> ## Transferring control to Linux (at address 80000)...
>
> Starting kernel ...
>
> flushing dcache successfully.

看着好像已经okay了，不过有个地方需要重点解释一下（上面黄色部分）。

> 还记得我们在“[u-boot启动流程分析(2)\_板级(board)部分](/u-boot/boot_flow_2.html)”中，介绍u-boot relocation的时候，提到过：“u-boot会被relocated到memory的高端位置执行”。上面“Current stack ends at 0x3ffbc4f0 ”可以佐证（u-boot代码当前的栈是在0x3ffbc4f0处，是高端地址）。
>
> 这样做的好处很明显：kernel是在低端运行（例如0x80000之后），u-boot在高端，相隔十万八千里，互不干涉。
>
> 与此同时，booti在boot kernel之前，将dtb文件也搬到高端地址了（000000003ffb8000），这样做可以避免kernel在执行的时候，破坏内存中的device tree信息。挺好！

#### 4. 修改kernel代码，点亮LED

经过上面的步骤，kernel貌似被成功boot了，但怎么证明呢？

在kernel的入口处点一下LED吧，改动的代码如下（不过多解释，也不再上传到github了，太野了~~~）：

> diff --git a/arch/arm64/kernel/head.S b/arch/arm64/kernel/head.S   
> index 85da0f5..449feae 100644   
> --- a/arch/arm64/kernel/head.S   
> +++ b/arch/arm64/kernel/head.S   
> @@ -210,6 +210,14 @@ section\_table:   
> #endif   
>   
> ENTRY(stext)   
> +loop\_test:   
> + ldr x1, =0xffffffff   
> + ldr x0, =0xe01b0000   
> + str x1, [x0]   
> + ldr x0, =0xe01b0008   
> + str x1, [x0]   
> + b loop\_test  
> +   
> bl preserve\_boot\_args   
> bl el2\_setup // Drop to EL1, w20=cpu\_boot\_mode   
> mov x23, xzr // KASLR offset, defaults to 0

再次编译后，按照第3章的步骤，再次boot之，应该就能看到灯亮了。虽然只是小小的一步，但后面的事情就好办了。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_booti.html)。
