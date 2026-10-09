---
title: "基于Hikey的\"Boot from USB\"调试"
date: 2016-12-20T22:36:53+08:00
url: "/x_project/hikey_usb_boot.html"
gid: "364"
emlog_type: "blog"
summary: "话说在半年前，乐美客送给蜗窝几块Hikey(乐美客版)开发板 [1] ，不过由于太忙，就一直把它们放在角落里思考人生，因此甚是愧疚。这几天，闲来无事，翻了下Hikey的资料，觉得挺有意思，就想花点时间让“ X Project ”在这个板子上跑起来。当然，按照“规矩”，先从“ 【任务1】启动过程-Boot from USB ”做起，记录如下。"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["USB", "boot", "u-boot", "spl", "hikey", "Hi6220V100"]
views: 11618
comment_count: 1
aliases:
  - "/x_project/364.html"
  - "/364.html"
---

## 1. 前言

话说在半年前，乐美客送给蜗窝几块Hikey(乐美客版)开发板[1]，不过由于太忙，就一直把它们放在角落里思考人生，因此甚是愧疚。这几天，闲来无事，翻了下Hikey的资料，觉得挺有意思，就想花点时间让“[X Project](/sort/x_project)”在这个板子上跑起来。当然，按照“规矩”，先从“[【任务1】启动过程-Boot from USB](/forum/15.html)”做起，记录如下。

## 2. Hikey介绍

说实话，作为一块开发板，Hikey有着国产平台的通病----资料匮乏，但它的source code却非常完整：

> 除ROM code之外的所有代码，都能在github上看到源码，这对ARM linux的学习（“[X Project](/sort/x_project)”的关注点）来说，是非常有用的。

另外，之所以觉得这块板子很有意思，是因为海思的这颗SOC----[Hi6220V100](https://github.com/96boards/documentation/blob/master/ConsumerEdition/HiKey/HardwareDocs/Hi6220V100_Multi-Mode_Application_Processor_Function_Description.pdf)[2]，它有如下的处理器架构：

[![Hi6220V100_SOC_ARCH](/content/uploadfile/201612/62b2298744793b5d87787b6c16eb688520161220143652.gif "Hi6220V100_SOC_ARCH")](/content/uploadfile/201612/ecc7dd6296f3c16d7ee954e6d0c9600c20161220143651.gif)

图片1 Hi6220V100 SOC Architecture

> 该SOC包含两个处理器子系统：
>
> MCU subsystem，里面有一个Cortex-M3的核，用于充电管理、电源管理等，也包括Boot code的USB download协议（猜测）；
>
> ACPU(这个缩写也太逗了，哈哈) subsystem，采用CCI-400互联总线（CoreLink）协议，支持8个Cortex-A53核（2个cluster[3]，每个cluster包含4个完全一样 A53核）。

基于上述的架构，Hikey USB boot的流程如下：

[![Hi6220V100_USB_BOOT](/content/uploadfile/201612/fe7a8c34e063b4136c6fb3ca1eb3975420161220143653.gif "Hi6220V100_USB_BOOT")](/content/uploadfile/201612/5b04128ebcb2b889fc8008e5ac44c81720161220143652.gif)

图片2 Hi6220V100 USB BOOT

注1：网上没有官方的spec介绍USB boot流程，上面的流程是我根据github上的开源代码，推测出来的，具体可参考：

> 1）l-loader，[https://github.com/96boards/l-loader.gi](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")[t](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")，其中的[start.S](https://github.com/96boards/l-loader/blob/master/start.S)即为上面图片中的“l-loader”，它是一段运行于Cortex-M3的汇编代码。另外由链接脚本（[l-loader.lds](https://github.com/96boards/l-loader/blob/master/l-loader.lds)）可知，它的执行位置0xf9800800。
>
> 2）ARM Trusted Firmware BL1，[https://github.com/96boards/arm-trusted-firmware/tree/hikey/bl1](https://github.com/96boards/arm-trusted-firmware/tree/hikey/bl1 "https://github.com/96boards/arm-trusted-firmware/tree/hikey/bl1")，l-loader正确初始化Cortex-A53之后，会将A53的控制权交给ARM Trusted Firmware，首先运行的是BL1，对Hikey来说，BL1的运行地址为0xf9801000（参考BL1\_RO\_BASE的定义）。
>
> 3）[https://github.com/96boards/l-loader.gi](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")[t](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")中有一个脚本（[gen\_loader.py](https://github.com/96boards/l-loader/blob/master/gen_loader.py)），可以将l-loader和BL1打包生成一个二进制文件，然后通过[hisi-idt.py](http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py)脚本，将这个二进制文件下载到0xf9800800处执行。

注2：Hikey的官方Image并没有使用常规的bootloader（u-boot等），而是用ARM Trusted Firmware代替了bootloader的功能，因此它的boot过程为：l-loader---->ARM Trusted Firmware(BL1, BL2, BL3等)---->Linux kernel。另外，ARM Trusted Firmware也集成了Android的fast boot功能，用起来还是很方便的。感兴趣的同学可以研究一下相关的source code。

## 3. 移植u-boot SPL到Hikey中

本章将根据第2章罗列的信息，基于“[X Project](/sort/x_project)”有关的文档，尝试将u-boot的SPL跑在Hikey开发板上，并点亮一盏灯，步骤如下。

#### 3.1 修改“[X Project](/sort/x_project)”的编译脚本，加入对Hikey的支持

不再详细描述修改步骤，具体可参考下面的patch：

> [[xprj, hikey] support hikey.](https://github.com/wowotechX/build/commit/030be3ea25a4d103ca515d898e95d33b849b89db)

#### 3.2 修改“[X Project](/sort/x_project)”的u-boot，增加对Hikey SPL的支持

mainline的u-boot已经支持了Hikey，但没有使能SPL功能，这刚好给我们大显身手的机会，步骤如下：

1）修改“arch/arm/Kconfig”，找到config TARGET\_HIKEY配置项，增加select SUPPORT\_SPL和select SPL，以支持SPL功能

> config TARGET\_HIKEY   
> bool "Support HiKey 96boards Consumer Edition Platform"   
> select ARM64   
> + select SUPPORT\_SPL   
> + select SPL  
> select DM   
> select DM\_GPIO   
> select DM\_SERIAL

2）修改完成后，在build目录执行make uboot-config，打开配置界面后，直接保存退出，从新生成config文件，具体可参考：

> [https://github.com/wowotechX/u-boot/blob/1775dca1f14df5b3ba0884c54b665f91fff24933/configs/hikey\_defconfig](https://github.com/wowotechX/u-boot/blob/1775dca1f14df5b3ba0884c54b665f91fff24933/configs/hikey_defconfig "https://github.com/wowotechX/u-boot/blob/1775dca1f14df5b3ba0884c54b665f91fff24933/configs/hikey_defconfig")

3）修改include/configs/hikey.h文件，增加SPL有关的TEXT配置，如下（黄色部分比较重要）：

> #define CONFIG\_SPL\_TEXT\_BASE 0xf9801000   
> #define CONFIG\_SPL\_MAX\_SIZE (1024 \* 20)  
> #define CONFIG\_SPL\_BSS\_START\_ADDR (CONFIG\_SPL\_TEXT\_BASE + \   
> CONFIG\_SPL\_MAX\_SIZE)   
> #define CONFIG\_SPL\_BSS\_MAX\_SIZE (1024 \* 12)   
> #define CONFIG\_SPL\_STACK (CONFIG\_SPL\_BSS\_START\_ADDR + \   
> CONFIG\_SPL\_BSS\_MAX\_SIZE + \   
> 1024 \* 12)

4）修改board/hisilicon/hikey/hikey.c，加入两个和SPL有关的函数实现，board\_init\_f和panic，并在board\_init\_f中点亮一盏LED灯，代码如下：

> +#ifdef CONFIG\_SPL\_BUILD   
> +void board\_init\_f(ulong bootflag)   
> +{   
> + /\* GPIO4\_2(User LED3), 0xF7020000, GPIODIR(0x400), GPIODAT2(0x10) \*/   
> + writel(readl(0xF7020400) | (1 << 2), 0xF7020400);   
> + writel(readl(0xF7020010) | 0xFF, 0xF7020010);   
> + while (1);   
> +}   
> +   
> +void panic(const char \*fmt, ...)   
> +{   
> +}   
> +#endif

其中LED有关的配置可参考Hikey（乐美客版）的原理图[7]以及[Hi6220V100](https://github.com/96boards/documentation/blob/master/ConsumerEdition/HiKey/HardwareDocs/Hi6220V100_Multi-Mode_Application_Processor_Function_Description.pdf)的spec[2]。

修改完毕后，编译生成u-boot-spl.bin，留作后用。

#### 3.3 单独编译出l-loader

从[https://github.com/96boards/l-loader.gi](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")[t](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")中将l-loader单独编译出，并保存在“[X Project](/sort/x_project)”的tools/hisilicon目录中，留作后用，如下：

> [https://github.com/wowotechX/tools/blob/hikey/hisilicon/img\_loader.bin](https://github.com/wowotechX/tools/blob/hikey/hisilicon/img_loader.bin "https://github.com/wowotechX/tools/blob/hikey/hisilicon/img_loader.bin")

注3：l-loader的编译方法，这里不再详细介绍（无非就是下载一个gcc-arm-linux-gnueabihf交叉编译器，稍微修改一下[l-loader.git](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")的Makefile文件）。

#### 3.4 将[gen\_loader.py](https://github.com/96boards/l-loader/blob/master/gen_loader.py)和[hisi-idt.py](http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py)保存到“[X Project](/sort/x_project)”的tools/hisilicon目录中

如下：

> [https://github.com/wowotechX/tools/blob/hikey/hisilicon/gen\_loader.py](https://github.com/wowotechX/tools/blob/hikey/hisilicon/gen_loader.py "https://github.com/wowotechX/tools/blob/hikey/hisilicon/gen_loader.py")
>
> [https://github.com/wowotechX/tools/blob/hikey/hisilicon/hisi-idt.py](https://github.com/wowotechX/tools/blob/hikey/hisilicon/hisi-idt.py "https://github.com/wowotechX/tools/blob/hikey/hisilicon/hisi-idt.py")

#### 3.5 修改“[X Project](/sort/x_project)”的编译脚本，增加Hikey u-boot-spl的运行命令

如下：

> img-loader=$(TOOLS\_DIR)/$(BOARD\_VENDOR)/img\_loader.bin   
> uboot-spl-bin=$(UBOOT\_OUT\_DIR)/spl/u-boot-spl.bin   
> gen-loader=$(TOOLS\_DIR)/$(BOARD\_VENDOR)/gen\_loader.py   
> hisi-idt=$(TOOLS\_DIR)/$(BOARD\_VENDOR)/hisi-idt.py   
>   
> spl-run:   
> # generate SPL image   
> sudo python $(gen-loader) -o spl.img --img\_loader=$(img-loader) --img\_bl1=$(uboot-spl-bin)   
> sudo python $(hisi-idt) --img1=spl.img -d /dev/ttyUSB0  
> rm -f spl.img

主要思路为：

1）使用[gen\_loader.py](https://github.com/96boards/l-loader/blob/master/gen_loader.py)脚本将img\_loader.bin和u-boot-spl.bin打包在一起，生成spl.img文件。

2）使用[hisi-idt.py](http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py)将spl.img下载到板子中运行。

#### 3.6 运行并测试

按照[1]中的步骤，为Hikey供电，并让它进入USB boot模式，然后在“[X Project](/sort/x_project)”的build目录中执行make spl-run即可。观察Hikey的LED灯，应该有一个亮了，说明移植成功。

## 4. 参考文档

[1] [http://wiki.lemaker.org/HiKey(LeMaker\_version):Quick\_Start/zh-hans](http://wiki.lemaker.org/HiKey(LeMaker_version):Quick_Start/zh-hans "http://wiki.lemaker.org/HiKey(LeMaker_version):Quick_Start/zh-hans")

[2] [Hi6220V100](https://github.com/96boards/documentation/blob/master/ConsumerEdition/HiKey/HardwareDocs/Hi6220V100_Multi-Mode_Application_Processor_Function_Description.pdf)

[3] [Linux CPU core的电源管理(2)\_cpu topology](/pm_subsystem/cpu_topology.html)

[4] Hikey l-loader，[https://github.com/96boards/l-loader.gi](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")[t](https://github.com/96boards/l-loader.git "https://github.com/96boards/l-loader.git")

[5] Hikey USB download脚本，[http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py](http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py "http://builds.96boards.org/releases/reference-platform/aosp/hikey/15.10/bootloader/hisi-idt.py")

[6] ARM Trusted Firmware, [https://github.com/96boards/arm-trusted-firmware.git](https://github.com/96boards/arm-trusted-firmware.git "https://github.com/96boards/arm-trusted-firmware.git")

[7] Hikey（乐美客版）原理图，[http://mirror.lemaker.org/LeMaker%20Hikey%20Schematic.pdf](http://mirror.lemaker.org/LeMaker%20Hikey%20Schematic.pdf "http://mirror.lemaker.org/LeMaker%20Hikey%20Schematic.pdf")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/hikey_usb_boot.html)。
