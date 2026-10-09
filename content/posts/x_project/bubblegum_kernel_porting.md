---
title: "X-009-KERNEL-Linux kernel的移植(Bubblegum-96平台)"
date: 2016-08-19T22:38:39+08:00
url: "/x_project/bubblegum_kernel_porting.html"
gid: "326"
emlog_type: "blog"
summary: "本文将以“ X Project ”的“ 【任务3】Linux kernel的配置、编译、加载与启动 ”为契机，介绍将Linux kernel移植到一个新的平台上的基本步骤，包括kernel以及device tree的配置、编译、二进制文件的生成等。 注1：本文的硬件基于ARM64架构，kernel基于“ X Project ”初始的“ Linux 4.6-rc5 ”版本"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Kernel", "x", "project", "porting", "dtb"]
views: 12104
comment_count: 2
aliases:
  - "/x_project/326.html"
  - "/326.html"
---

#### 1. 前言

本文将以“[X Project](/forum/)”的“[【任务3】Linux kernel的配置、编译、加载与启动](/forum/51.html)”为契机，介绍将Linux kernel移植到一个新的平台上的基本步骤，包括kernel以及device tree的配置、编译、二进制文件的生成等。

注1：本文的硬件基于ARM64架构，kernel基于“[X Project](/forum/)”初始的“[Linux 4.6-rc5](https://github.com/wowotechX/linux/tree/02da2d72174c61988eb4456b53f405e3ebdebce4)”版本

#### 2. kernel配置

我们在“[Linux kernel内核配置解析(1)\_概述(基于ARM64架构)](/linux_kenrel/kernel_config_overview.html)”提到过，Linux kernel的配置项非常繁多，初接触的时候，会产生深深的恐惧感。但是，尽管如此，得益于Linux kernel超高的设计水平，它的移植过程却又非常简单（甚至比u-boot还简单）。因此，从“好读书而不求甚解”的角度出发，在开始移植的时候，我们可以按照如下的步骤配置Linux kernel：

1）在linux目录下，执行menuconfig命令，得到一个默认的.config文件，然后保存为板子所对应的defconfig文件。

> cd ./linux   
> make ARCH=arm64 menuconfig   
> …
>
> cp .config arch/arm64/configs/bubblegum\_defconfig

2）在“x project”的build脚本中，添加一个用于快速配置Linux kernel命令。

> kernel-config:   
>  mkdir -p $(KERNEL\_OUT\_DIR)   
>  cp -f $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(BOARD\_NAME)\_defconfig $(KERNEL\_OUT\_DIR)/.config   
>  make -C $(KERNEL\_DIR) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) menuconfig   
>  cp -f $(KERNEL\_OUT\_DIR)/.config $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(BOARD\_NAME)\_defconfig

3）删减一下配置项

按理说，默认生成的配置文件就可以工作了（爽呆了吧~~~~~~~~）。不过，默认配置需要编译的内容太多了，导致编译速度太慢，我们可以disable掉一些配置项（可以随心所欲），我的操作步骤如下：

> cd ./build   
> make kernel-config

将下面几个菜单里面的配置项，能disable的全部disable掉（具体过程我就不贴了，大家可以自由发挥，因为这是个力气活）：

> [ ] Networking support   
> Device Drivers --->   
> Firmware Drivers --->   
> File systems --->   
> [\*] Virtualization --->   
> Security options --->   
> -\*- Cryptographic API --->   
> Library routines --->

最终的config文件可参考：

> [https://github.com/wowotechX/linux/blob/f1b4e7056afd516089b10ec1d36c396db310db37/   
> arch/arm64/configs/bubblegum\_defconfig](https://github.com/wowotechX/linux/blob/f1b4e7056afd516089b10ec1d36c396db310db37/ arch/arm64/configs/bubblegum_defconfig)

4）编译

编译开始前，我们也先做一个快捷的编译脚本：

> kernel:   
>  mkdir -p $(KERNEL\_OUT\_DIR)   
>  make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) $(BOARD\_NAME)\_defconfig   
>  make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH)

然后执行编译命令：

> cd ./build   
> make kernel

编译完成后，即可生成所需的Image文件：

> ls out/linux/arch/arm64/boot/ -lh   
> total 6.5M   
> drwxr-xr-x 22 pengo pengo 4.0K 2016-08-15 01:46 dts   
> -rwxr-xr-x 1 pengo pengo 4.5M 2016-08-15 01:46 Image   
> -rw-r--r-- 1 pengo pengo 2.0M 2016-08-15 01:46 Image.gz

#### 3. device tree移植

在新时代中，不扯扯的device tree，总觉得太土包了。不过在ARM64中，这不是土包不土包的事情，device tree是强制的（具体可参考本站device tree有关的分析文章[1][2][3]）。在本文的kernel移植中，device tree的移植也是必须步骤，因为：

> u-boot在boot kernel的时候，要么使用传统的atags的方式，要么使用device tree的方式，向kernel传递参数。而kernel的ARM64代码不支持atags了，device tree就成了唯一选项了。
>
> 那么能不能暂时不给呢？不能，因为u-boot会罢工。

闲话少说，我们可以按照如下步骤移植device tree：

1）在arch/arm64/Kconfig.platforms中，添加以“ARCH\_”开头的platform配置（可以参考已有的配置项），如下：

> diff --git a/arch/arm64/Kconfig.platforms b/arch/arm64/Kconfig.platforms   
> index efa77c1..494e83d 100644   
> --- a/arch/arm64/Kconfig.platforms   
> +++ b/arch/arm64/Kconfig.platforms   
> @@ -174,4 +174,9 @@ config ARCH\_ZYNQMP   
>  help   
>  This enables support for Xilinx ZynqMP Family   
>   
> +config ARCH\_OWL   
> + bool "Actions OWL 64-bit SoC Family"   
> + help   
> + This enables support for Actions OWL based SoCs like the S900.   
> +

2） 新建板子对应的dts文件

首先，在arch/arm64/boot/dts/创建一个厂商的目录（同样，可以参考已有内容）：

> mkdir arch/arm64/boot/dts/actions

然后修改arch/arm64/boot/dts/Makefile，增加我们新建的目录，如下：

> pengo@ubuntu:~/work/xprj/linux$ git diff arch/arm64/boot/dts/Makefile   
> diff --git a/arch/arm64/boot/dts/Makefile b/arch/arm64/boot/dts/Makefile   
> index 330fae9..33e311c 100644   
> --- a/arch/arm64/boot/dts/Makefile   
> +++ b/arch/arm64/boot/dts/Makefile   
> @@ -1,3 +1,4 @@   
> +dts-dirs += actions  
> dts-dirs += al   
> dts-dirs += altera   
> dts-dirs += amd

最后，在actions目录下，添加对应的dts和Makfile文件（同样，可以参考已有内容）：

> pengo@ubuntu:~/work/xprj/linux$ cat arch/arm64/boot/dts/actions/\*   
> dtb-$(CONFIG\_ARCH\_OWL) += s900-bubblegum.dtb   
> always := $(dtb-y)   
> subdir-y := $(dts-dirs)   
> clean-files := \*.dtb   
> /\*   
> \* dts file for Bubblegum-96 Development Board   
> \*   
> \* Copyright (C) 2016, wowotech.   
> \*   
> \*/
>
> /dts-v1/;   
>   
> / {   
>  model = "Bubblegum-96 Development Board";   
>  compatible = "actions,s900-bubblegum", "actions,s900";   
> };

3） 重新配置kernel，使能ARCH\_OWL

> make kernel-config
>
> Platform selection --->   
> [\*] Actions OWL 64-bit SoC Family

4） 小小的修改一下编译脚本，针对性的编译Image和dtb，如下：

> - make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH)   
> + make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) Image dtbs

5）再次编译

> make kernel

输出结果：

> pengo@ubuntu:~/work/xprj/build$ ls out/linux/arch/arm64/boot/dts/actions/   
> s900-bubblegum.dtb
>
> pengo@ubuntu:~/work/xprj/build$ ls out/linux/arch/arm64/boot/   
> dts Image Image.gz

OK成功了。

#### 4. kernel启动

到目前为止，我们好像没有涉及任何的代码逻辑，这就是Linux kernel的伟大之处：复杂而又简单。 让我们来顺着kernel的启动过程，简单的梳理一下。

##### 4.1 Linux kernel要从什么位置启动呢？

由“[u-boot的移植说明](/x_project/bubblegum_uboot_porting.html)”可知，u-boot在编译到时候，需要通过“TEXT\_BASE”指定其运行地址。但在本文kernel的移植过程中，好像没有这样的操作，为什么呢？我们可以从如下的角度回答这个问题。

1）kernel的运行地址到底是什么？

> 参考”[ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html)”的介绍，kernel的运行地址，是在kernel的链接脚本（[arch/arm64/kernel/vmlinux.lds.S](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/kernel/vmlinux.lds.S)）中，由CONFIG\_ARM64\_VA\_BITS所指定的一个虚拟地址，例如0xffffffc0-00000000（CONFIG\_ARM64\_VA\_BITS等于39的时候）。

2）虚拟地址？bootloader能把kernel加载到一个虚拟地址中并运行呢？

这当然是不可能，也是不需要的，因为：

> a）kernel在刚刚执行的时候，MMU还没有使能，kernel“所看到”的地址，都还是物理地址。
>
> b）由于编译的时候使用的都是虚拟地址（例如某一个变量的地址），因此在MMU使能之前，kernel的代码都是位置无关的（具体可参考“[arch/arm64/kernel/head.S](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/kernel/head.S)”中的注释）。如果需要访问某个虚拟地址，则需要adr\_l等指令，获取指定虚拟地址的物理地址（利用当前的PC值和符号值的差异计算获得）。
>
> c）MMU使能后，无论kernel运行的物理地址是什么，它都会把自己map到对应的虚拟地址上，之后就可以欢快的执行了。

3）那么要把kernel放在什么地方（物理地址）运行呢？

答案是你想放什么地方就可以放到什么地方，但有一点需要注意：

> 上面我们讲过，kernel的代码段（运行地址）是一个由CONFIG\_ARM64\_VA\_BITS所指定的一个虚拟地址，例如0xffffffc0-00000000。由于kernel的代码是位置无关的，因此我们可以把kernel image下载到RAM中的任何位置执行。
>
> 但是，参考”[ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html)”中有关\_\_PHYS\_OFFSET的定义可知，kernel在KERNEL\_START（例如0xffffffc0-00000000，也即kernel所处于的物理地址对应的虚拟地址）之前，预留出来了大小为TEXT\_OFFSET的空间，用于保存内核的页表。
>
> 因此，我们在放置kernel（例如从外部存储介质读取到RAM中）的时候，需要为kernel预留TEXT\_OFFSET所定义的空间（例如0x80000）。例如，如果DRAM的起始地址是0x0，我们需要把kernel的image文件copy到0x80000处。

##### 4.2 kernel启动过程分析

可参考本站相关的文章[4]，这里不再详细说明了。

#### 5. 参考文档

[1] [Device Tree（一）：背景介绍](/device_model/why-dt.html)

[2] [Device Tree（二）：基本概念](/device_model/dt_basic_concept.html)

[3] [Device Tree（三）：代码分析](/device_model/dt-code-analysis.html)

[4] [ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_kernel_porting.html)。
