---
title: "Linux kernel内核配置解析(1)_概述(基于ARM64架构)"
date: 2016-08-10T23:20:08+08:00
url: "/linux_kenrel/kernel_config_overview.html"
gid: "323"
emlog_type: "blog"
summary: "对刚接触Linux kernel的同学来说，遇到的第一个问题就是：我该从哪里入手？、 话说Linux kernel的打开方式是多种多样的：从简单的设备驱动入手；从源代码的目录结构入手；从kernel的启动过程入手；从大的功能模块入手；等等。不管怎样，每条都是正途（条条大路通罗马嘛）。 而本文（以及随后的系列文章），将从Linux kernel的配置项入手，从整体上认识Linux kernel。之所"
author: "wowo"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["Linux", "Kernel", "内核", "配置项", "menuconfig"]
views: 25002
comment_count: 2
aliases:
  - "/linux_kenrel/323.html"
  - "/323.html"
---

#### 1. 前言

对刚接触Linux kernel的同学来说，遇到的第一个问题就是：我该从哪里入手？、

话说Linux kernel的打开方式是多种多样的：从简单的设备驱动入手；从源代码的目录结构入手；从kernel的启动过程入手；从大的功能模块入手；等等。不管怎样，每条都是正途（条条大路通罗马嘛）。

而本文（以及随后的系列文章），将从Linux kernel的配置项入手，从整体上认识Linux kernel。之所以这么做，原因有二：

> 1）Linux kernel的配置项数目繁多，以至于进行kernel移植的时候，看到menuconfig界面后，会有深深的恐惧感（可参考下面图片1）。
>
> 2）配置项的目的，是功能配置和功能开关，从一定程度上可以看出一个软件的功能模块划分。以Linux kernel为例，Kconfig所呈现出来的树状结构，从功能划分的角度看，比source code的目录结构还清晰。

注1：本系列文章使用的Linux kernel版本是“[X Project](/forum/)”所用的“[Linux 4.6-rc5](https://github.com/wowotechX/linux/commit/02da2d72174c61988eb4456b53f405e3ebdebce4)”，具体可参考“[https://github.com/wowotechX/linux.git](https://github.com/wowotechX/linux.git "https://github.com/wowotechX/linux.git")”。

#### 2. Kernel配置项初识

Linux kernel的配置项，是以架构（ARCH）为单位，通过Kconfig语言组织在一起的。以ARM64为例，其Kconfig的入口位于：

> arch/arm64/Kconfig

在Kernel根目录下以“ARCH=arm64”为参数，执行make menuconfig，可以得到如下的配置界面：

> make ARCH=arm64 menuconfig

[![kernel_menuconfig](/content/uploadfile/201608/09aa28c7104ce75c5d80ce602344219b20160810152007.gif "kernel_menuconfig")](/content/uploadfile/201608/a731b44c081c641cfd21bdba02a61f6220160810152005.gif)

图片1 Kernel\_menuconfig

第一个画面，还可以接受，毕竟画风清爽。但点进到二级菜单，脑袋就大了。不过不着急，我们一层一层的分析。

开始之前，先交代一下分析的手段，很简单，要点有四：

> 结合Kconfig文件；
>
> 跟随menuconfig的菜单项；
>
> 加上强大的Google；
>
> 必要时阅读source code。

另外，鉴于篇幅问题，本文只介绍Kconfig的一级菜单（就是图片1所能看到的部分），相当于一个索引，后续文章会一个一个展开描述。

#### 3. 一级菜单

本章我们将根据arch/arm64/Kconfig文件，对menuconfig的一级菜单进行简要的分析，目的是从实际的例子出发，理解Kconfig语言的语法，一级Linux kernel配置项的整体结构。具体请参考如下表格：

|  |  |  |
| --- | --- | --- |
| 配**置项** | **Kconfig文件位置** | **功能说明** |
| ARM64架构的默认配置项 | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig) | 指定ARCH为ARM64之后，ARM64的Kconfig会默认帮我们确定众多的配置项，例如CONFIG\_64BIT、CONFIG\_MMU、CONFIG\_OF等等。这些配置项不会体现在menuconfig的菜单中，但可以在最终生成的config文件中看到。 |
| General setup | [init/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/init/Kconfig)   位于menu "General setup"和对应的endmenu之间 | 该配置项由“menu … endmenu”定义，是一个配置菜单，表示一类配置的集合（参考上面图片1，“--->”结尾的配置项都是菜单项，按Enter直接进入对应的菜单界面）；    主要用于配置和功能无关的的通用选项，例如kernel的版本号、压缩方式、等等。 |
| loadable module | [init/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/init/Kconfig)   由“menuconfig MODULES”定义 | menuconfig和menu不同，是一个可以选择是否开启的菜单（参考图片1中的“[\*]”）；    用于配置内核“模块”有关的特性。 |
| block device | [block/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/block/Kconfig)   由“menuconfig BLOCK”定义 | 内核块设备有关的特性。 |
| Platform selection | [arch/arm64/Kconfig.platforms](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig.platforms)   位于menu "Platform selection"和endmenu之间 | 用于配置和具体平台有关的配置项，如SUNIX、HISI等；    自从ARM64把“mach-xxx”目录抛弃之后，这里可能是各个平台可自行发挥的最后一个空间了。 |
| PCI Bus support | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   drivers/pci/Kconfi | PCI总线有关的特性。 |
| ACPI support | drivers/acpi/Kconfig | ACPI总线有关的特性。 |
| Kernel Features | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   kernel/Kconfig.preempt    kernel/Kconfig.hz    mm/Kconfig    位于menu "Kernel Features"和对应的endmenu之间 | Linux kernel的核心功能的配置，如进程管理、内存管理、等等。是Linux kernel配置项中最复杂的一类。 |
| Boot options | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   位于menu "Boot options"和对应的endmenu之间 | 用于配置和内核启动有关的功能，如默认的Command line、UEFI支持等。 |
| Userspace binary formats | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   fs/Kconfig.binfmt    位于menu "Userspace binary formats"和对应的endmenu之间 | 用于配置用户空间二进制的格式。 |
| Power management | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   kernel/power/Kconfig    位于menu "Power management options"和对应的endmenu之间 | Linux kernel电源管理有关的特性。 |
| CPU Power Management | [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)   drivers/cpuidle/Kconfig    drivers/cpufreq/Kconfig    位于menu "CPU Power Management"和对应的endmenu之间 | CPU有关的电源管理特性，如cpuidle、cpufreq等；    这是新版kernel的一大改进，将CPU有关的电源管理功能，抽象成一个顶层功能，和系统的电源管理并列。 |
| Networking support | [net/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/net/Kconfig) | 网络有关的特性。 |
| Device Drivers | [drivers/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/drivers/Kconfig) | 设备驱动有关的配置项。 |
| Firmware Drivers | [drivers/firmware/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/drivers/firmware/Kconfig)   … | Firmware有关的配置项。 |
| File systems | [fs/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/fs/Kconfig) | 文件系统有关的配置项。 |
| Virtualization | [arch/arm64/kvm/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/kvm/Kconfig) | 虚拟化有关的配置项。 |
| Kernel hacking | arch/arm64/Kconfig.debug | Kernel调试有关的配置项。 |
| Security options | [security/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/security/Kconfig) | 安全特性有关的配置项。 |
| Cryptographic API | [crypto/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/crypto/Kconfig)   [arch/arm64/crypto/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/crypto/Kconfig) | 加密算法有关的配置项。 |
| Library routines | [lib/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/lib/Kconfig) | 用于配置常用的library，如CRC16等。 |

#### 4. 总结

本文只是一个引子，以ARM64平台为例，大概介绍了Linux内核配置的基本结构。后续将会以一个个专题为单位，展开介绍。

鉴于内核配置涉及到了Linux kernel的所有模块，因此该系列文档将是一个大工程，后续所有的文件将包括（此处先留位占空，后面会慢慢补充完善：

> Linux kernel内核配置解析(2)\_ARM64架构特有的配置项
>
> Linux kernel内核配置解析(3)\_General setup
>
> Linux kernel内核配置解析(4)\_Kernel Features
>
> Linux kernel内核配置解析(5)\_Boot options
>
> Linux kernel内核配置解析(6)\_Kernel hacking
>
> （等等）
>
> Linux kernel内核配置解析(n)\_配置项汇整。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/linux_kenrel/kernel_config_overview.html)。
