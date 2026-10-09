---
title: "X-016-KERNEL-串口驱动开发之驱动框架"
date: 2016-11-10T22:12:03+08:00
url: "/x_project/serial_driver_porting_1.html"
gid: "353"
emlog_type: "blog"
summary: "在过去的一段时间里，蜗窝上发表了一系列的关于内核各个子系统的分析文章，设备模型、device tree、中断子系统、clock framework、电源管理、GPIO、pinctrl等等，这些文章重理论、轻实践。随着“ X Project ”的进行，我们渐渐有机会把这些缺失的实践慢慢补回来。 串口驱动是进入Linux kernel之后最先遭遇的一个驱动，虽然不是很复杂，但要素齐全，使用到了kern"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["driver", "serial", "框架", "串口", "驱动", "platform_driver"]
views: 9138
comment_count: 0
aliases:
  - "/x_project/353.html"
  - "/353.html"
---

## 1. 前言

在过去的一段时间里，蜗窝上发表了一系列的关于内核各个子系统的分析文章，设备模型、device tree、中断子系统、clock framework、电源管理、GPIO、pinctrl等等，这些文章重理论、轻实践。随着“[X Project](/sort/x_project)”的进行，我们渐渐有机会把这些缺失的实践慢慢补回来。

串口驱动是进入Linux kernel之后最先遭遇的一个驱动，虽然不是很复杂，但要素齐全，使用到了kernel的各个子系统。因此我希望能借助串口驱动的开发过程，将这些子系统的使用一一串联起来，并记录为一份份单独的文章。

本文是这一系列文章的第一篇，借助串口驱动开发，学习Linux设备模型之下的驱动框架。

## 2. 驱动开发框架

Linux kernel中大部分设备可以归结为平台设备，因此大部分的驱动是平台驱动（patform driver）。得益于设备模型，Linux kernel平台驱动的开发有了一套非常固定的框架，总结如下（具体可参考[1][2]）：

1）模块的入口和出口

用于注册/注销platform driver，这一部分的代码基本固定，包括函数和变量的命名方式也可固定，如下：

> static int \_\_init AAA\_BBB\_init(void)   
> {   
> int ret;   
>   
> pr\_info("%s\n", \_\_func\_\_);   
>   
> ret = platform\_driver\_register(&AAA\_BBB\_platform\_driver);   
> if (ret < 0) {   
> pr\_err("AAA\_BBB\_platform\_driver register failed, ret = %d\n", ret);   
> return ret;   
> }   
> return 0;   
> }   
>   
> static void \_\_exit AAA\_BBB\_exit(void)   
> {   
> pr\_info("%s\n", \_\_func\_\_);   
>   
> platform\_driver\_unregister(&AAA\_BBB\_platform\_driver);   
> }
>
> module\_init(AAA\_BBB\_init);   
> module\_exit(AAA\_BBB\_exit);   
>   
> MODULE\_ALIAS("platform driver: AAA\_BBB");   
> MODULE\_DESCRIPTION("BBB driver for xxxx");   
> MODULE\_AUTHOR("wowo");   
> MODULE\_LICENSE("GPL v2");

其中AAA一般可以是厂商名、芯片名、芯片的系列名、等等，例如TI OMAP系列的芯片，AAA可以是omap。BBB一般是模块名，以本文的串口驱动为例，可以是serial或者uart。因此AAA\_BBB可以替换为omap\_serial。编写驱动的时候，直接将上面的copy出来，查找替换即可。

2）platform driver

基本的platform driver包含三要素：struct platform\_driver变量、probe/remove函数、用于和device tree匹配的match table，如下：

> static const struct of\_device\_id AAA\_BBB\_of\_match[] = {   
> {   
> .compatible = "xxx,xxx-BBB",  
> },   
> {   
> },   
> };   
> MODULE\_DEVICE\_TABLE(of, AAA\_BBB\_of\_match);   
>   
> static int AAA\_BBB\_probe(struct platform\_device \*pdev)   
> {   
> int ret = 0;   
>   
> const struct of\_device\_id \*match;   
>   
> dev\_info(&pdev->dev, "%s\n", \_\_func\_\_);   
>   
> match = of\_match\_device(AAA\_BBB\_of\_match, &pdev->dev);   
> if (!match) {   
> dev\_err(&pdev->dev, "Error: No device match found\n");   
> return -ENODEV;   
> }   
>   
> return ret;   
> }   
>   
> static int AAA\_BBB\_remove(struct platform\_device \*pdev)   
> {   
> dev\_info(&pdev->dev, "%s\n", \_\_func\_\_);   
>   
> return 0;   
> }   
>   
> static struct platform\_driver AAA\_BBB\_platform\_driver = {   
> .probe = AAA\_BBB\_probe,   
> .remove = AAA\_BBB\_remove,   
> .driver = {   
> .name = "AAA\_BBB",   
> .of\_match\_table = AAA\_BBB\_of\_match,   
> },   
> };

同理，上面的AAA\_BBB可以直接替换。另外有一点需要注意，AAA\_BBB\_of\_match中的.compatible需要和DTS文件中的compatible对应，一般格式是“厂商名称,芯片系列-模块名”，例如“actions,s900-serial” 。

3）头文件包含

上面的代码，使用到了很多kernel API，需要包含如下头文件：

> #include <linux/kernel.h>   
> #include
> <linux/init.h>  
> #include <linux/device.h>   
> #include
> <linux/platform\_device.h>   
> #include <linux/module.h>   
> #include
> <linux/of.h>   
> #include <linux/of\_device.h>

4）设备描述

需要在dts文件中，增加platform driver所要驱动设备的描述，例如：

> BBBx: [BBB@xxxxxxxx](mailto:BBB@xxxxxxxx) {   
> compatible = "xxx,xxx-BBB";  
> };

其中BBBx为dts节点的别名，用于方便在它处引用，为可选项。@xxxxxxxx一般为该模块的I/O起始地址，如果没有，可以写任意名称（或者留空），compatible需要和上面AAA\_BBB\_of\_match对应，例如“actions,s900-serial” 。

## 3. 串口驱动

基于上面描述，我们以Bubblegum-96平台的串口为例，编写如下代码（基本上都是使用查找替换操作，%s/AAA/owl/g, %s/BBB/serial/g）：

> [https://github.com/wowotechX/linux/commit/ff4955f391cd211ff85588f46b05099065ddeb07](https://github.com/wowotechX/linux/commit/ff4955f391cd211ff85588f46b05099065ddeb07 "https://github.com/wowotechX/linux/commit/ff4955f391cd211ff85588f46b05099065ddeb07")

注1：由于代码非常简单，这里就不解释了，有疑问的同学，可以直接在github上指定的代码行添加评论。

注2：这里的串口驱动和serial early console[3]共用一份代码，为了方便调试，在串口驱动ready之前，我们暂时保留early console原封不动。

注3：开始写代码的时候，我们一般会为这个工作新建一个分支，在这个分支上工作OK的话，再merge回主分支，这也是代码开发的一个基本规则

> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ git fetch origin   
> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ git branch -a   
> \* x\_integration  
> remotes/origin/HEAD -> origin/x\_integration   
> remotes/origin/x\_integration   
> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ git rebase origin/x\_integration   
> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ git checkout -b serial\_dev  
> Switched to a new branch 'serial\_dev'   
> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ git branch   
> \* serial\_dev  
> x\_integration

完成代码后，编译并运行kernel，通过earlycon的打印，查看probe函数是否被执行。

## 4. 参考文档

[1] [Linux设备模型(8)\_platform设备](/device_model/platform_device.html)

[2] [Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)

[3] [X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/serial_driver_porting_1.html)。
