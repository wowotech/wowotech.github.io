---
title: "X-013-UBOOT-使能autoboot功能"
date: 2016-10-05T21:51:57+08:00
url: "/x_project/uboot_autoboot.html"
gid: "340"
emlog_type: "blog"
summary: "\r\n\t通过“X-012-KERNEL-serial \r\nearly console的移植”，早期的串口控制台已经ready，kernel的printk可以正确输出，“X \r\nProject”由此进入“文明”时代。基于此，后续的开发工作将会focus在linux kernel上，而u-boot，可以蜕化为其原始目标：boot \r\nkernel。\r\n\r\n\r\n\t在之前的测试和调试过程中，都是先进入u-b"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["boot", "u-boot", "bootm", "autoboot"]
views: 12260
comment_count: 6
aliases:
  - "/x_project/340.html"
  - "/340.html"
---

## 1. 前言

通过“[X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)”，早期的串口控制台已经ready，kernel的printk可以正确输出，“[X Project](/forum/)”由此进入“文明”时代。基于此，后续的开发工作将会focus在linux kernel上，而u-boot，可以蜕化为其原始目标：boot kernel。

在之前的测试和调试过程中，都是先进入u-boot的命令行，手动输入bootm命令，boot linux kernel。为了简化这个动作，有必要将u-boot的autoboot功能用起来。

所谓的autoboot，是指u-boot run起来之后，自动加载并执行linux kernel image的 过程。该功能非常简单，之所以写一篇文章，权当“[X Project](/forum/)”开发过程的一个记录。

## 2. 使能autoboot

#### 2.1 u-boot autoboot功能简介

u-boot autoboot功能的具体介绍可参考“[README.autoboot](https://github.com/wowotechX/u-boot/blob/x_integration/doc/README.autoboot)[1]”，总结来说：

1）通过CONFIG\_BOOTDELAY配置是否使用autoboot功能，是否在autoboot之前等待一段时间以便让用户输入从而进入命令行：

> Delay before automatically booting the default image;
>
> set to -1 to disable autoboot.
>
> set to -2 to autoboot with no delay and not check for abort (even when CONFIG\_ZERO\_BOOTDELAY\_CHECK is defined).

2）通过CONFIG\_BOOTCOMMAND配置boot kernel所使用的命令。

3）通过CONFIG\_BOOTARGS配置命令行参数。

4）其它等等。

#### 2.2 基于bubblegum-96配置并使能autoboot

以“[X Project](/forum/)”目前的情况来说，我们暂时只使用CONFIG\_BOOTDELAY和CONFIG\_BOOTCOMMAND两个即可，如下：

> /\* include/configs/bubblegum.h \*/
>
> #define CONFIG\_BOOTDELAY -2
>
> #define CONFIG\_BOOTCOMMAND "bootm 0x6400000"

其中CONFIG\_BOOTDELAY为-2，表示不需要任何delay；CONFIG\_BOOTCOMMAND即为我们在u-boot命令行敲入的用于boot kernel的指令。

注1：由于当前bubblegum-96的u-boot没有移植timer驱动，CONFIG\_BOOTDELAY为正值的时候无法正确使用（没有计时，也就没有timeout了）。

#### 2.3 简单的测试

为了方便测试，我在build makefile中添加了几个辅助命令，如下：

> #   
> # some help commands   
> #   
> spl-run:   
> sudo $(DFU\_DIR)/dfu $(BOARD\_NAME) $(SPL\_BASE) $(TOOLS\_DIR)/$(BOARD\_VENDOR)/splboot.bin 1
>
> uimage-load:   
> sudo $(DFU\_DIR)/dfu $(BOARD\_NAME) $(FIT\_UIMAGE\_BASE) $(UIMAGE\_ITB\_FILE) 0
>
> uboot-run:   
> sudo $(DFU\_DIR)/dfu $(BOARD\_NAME) $(UBOOT\_BASE) $(OUT\_DIR)/u-boot/u-boot-dtb.bin 1
>
> kernel-run: uimage-load uboot-run

按住ADFU键开机，执行make spl-run初始化DDR，然后执行make kernel-run，就可以直接启东到linux kernel了。具体可参考”[README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96)[2]”。

以上改动可参考如下patch：

> [https://github.com/wowotechX/u-boot/commit/59553f4c7583c002e9eb5e2ac7402a25699d51c6](https://github.com/wowotechX/u-boot/commit/59553f4c7583c002e9eb5e2ac7402a25699d51c6 "https://github.com/wowotechX/u-boot/commit/59553f4c7583c002e9eb5e2ac7402a25699d51c6")

## 3. 参考文档

[1] [README.autoboot](https://github.com/wowotechX/u-boot/blob/x_integration/doc/README.autoboot)

[2] [README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/uboot_autoboot.html)。
