---
title: "X-018-KERNEL-串口驱动开发之serial console"
date: 2016-11-18T22:25:12+08:00
url: "/x_project/serial_driver_porting_3.html"
gid: "356"
emlog_type: "blog"
summary: "本文是“ X Project ”串口驱动开发的第三篇，在第二篇“ uart driver框架 [1] ”的基础上，实现console驱动，并借助这个过程，理解如下知识： 1）从DTS regs字段中获取设备的I/O基址，并map出来供driver访问。这是device tree最基本的使用场景。 2）从DTS aliases中获取串口的索引号。这是device tree aliases功能的一个应"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "driver", "serial", "console", "aliases"]
views: 11412
comment_count: 1
aliases:
  - "/x_project/356.html"
  - "/356.html"
---

## 1. 前言

本文是“[X Project](/sort/x_project)”串口驱动开发的第三篇，在第二篇“[uart driver框架](/x_project/serial_driver_porting_2.html)[1]”的基础上，实现console驱动，并借助这个过程，理解如下知识：

> 1）从DTS regs字段中获取设备的I/O基址，并map出来供driver访问。这是device tree最基本的使用场景。
>
> 2）从DTS aliases中获取串口的索引号。这是device tree aliases功能的一个应用场景。
>
> 3）uart port—>line和console—>index之间的关系。

## 2. 从DTS regs字段中获取设备的I/O基址

大家应该记得我们在移植串口的“early console[2]”的时候，需要使用UART5的寄存器地址，那时直接在代码中用宏定义出来了，如下：

> #define UART5\_BASE (0xE012a000)

这种做法有一个明显的缺点：driver不具有通用性，如果寄存器地址换了怎么办？如果换个串口呢？如果同时支持多个串口呢？这时device tree的优势就体现出来了，driver可以在probe的时候动态的从dts中获取当前设备的寄存器地址，步骤如下：

1）在dts文件中增加regs字段

> serial5: serial@e012a000 {   
> compatible = "actions,s900-serial";   
> + reg = <0 0xe012a000 0 0x2000>; /\* UART5\_BASE \*/  
> };

其格式由dts文件的#address-cells和 #size-cells决定，它们都是2的时候，表示UART5的寄存器从0x00000000e012a000开始，size为0x0000000000002000。

2）在driver probe接口中，以IORESOURCE\_MEM为参数，调用platform\_get\_resource接口，以struct resource的形式，将上面定义的寄存器信息取出来，并保存在uart port的mapbase指针中

> + resource = platform\_get\_resource(pdev, IORESOURCE\_MEM, 0);   
> + if (!resource) {   
> + dev\_err(&pdev->dev, "No IO memory resource\n");   
> + return -ENODEV;   
> + }   
> + port->mapbase = resource->start;

其中“IORESOURCE\_MEM”表示要获取的资源类型是memory资源，0表示是第一个（如果有多个，可以以此传入1、2等等）。

3）调用devm\_ioremap\_resource接口，将资源map出来，driver就可以使用了

> + port->membase = devm\_ioremap\_resource(&pdev->dev, resource);  
> + if (IS\_ERR(port->membase)) {   
> + dev\_err(&pdev->dev, "Failed to map memory resource\n");   
> + return PTR\_ERR(port->membase);   
> + }   
> + port->iotype = UPIO\_MEM32;

同样，map出来之后，可以保存在uart port的membase指针中，同时需要把iotype设置为UPIO\_MEM32。

## 3. 从DTS aliases中获取串口的索引号

由于linux serial framework允许一个serial driver支持多个uart port，为了方便，我们会为这些串口编号，具体体现在struct uart\_port的line变量中，那用什么方法为port->line赋值呢？最好通过device tree，因为这样灵活啊。下面介绍一种通过aliases的方法。

以本文的UART5为例，dts文件中的节点名为：[serial@e012a000](mailto:serial@e012a000)，为了方便，我们给它添加了一个别名：serial5，这样就可以在别处引用。为了让driver可以获得该串口的编号（5），我们可以在dts中定义一个aliases，如下：

> + aliases {   
> + serial5 = &serial5;   
> + };

然后，在driver的probe中，调用of\_alias\_get\_id，就可以获得该编号：

> + port->line = of\_alias\_get\_id(pdev->dev.of\_node, "serial");  
> + if (port->line < 0) {   
> + dev\_err(&pdev->dev, "failed to get alias id, errno %d\n",   
> + port->line);   
> + return port->line;   
> + }

of\_alias\_get\_id的参数为“serial”，就是上面aliases左边除了数字的部分。

注1：大家可以思考一下这种方法的好处。

## 4. 完善console driver并测试之

1）把console driver的index也改成5

> .flags = CON\_PRINTBUFFER,   
> - .index = -1,   
> + .index = 5,  
> .data = &owl\_serial\_driver,

2）实现console driver的write接口

实现方法和[2]中的类似，只不过寄存器的基址是动态map出来的（具体可参考后面的patch文件[3]）。另外需要说明的是，driver中的操作对象都是struct uart\_port指针，但console的write接口是个例外，它使用struct console指针。也就是说，我们需要一个办法从struct console指针中得到对应的struct uart\_port指针。不着急，有办法（代码如下，大家自行理解即可）：

> static void owl\_console\_write(struct console \*con, const char \*s, unsigned n)   
> {   
> + struct uart\_driver \*driver = con->data;   
> + struct uart\_port \*port = driver->state[con->index].uart\_port;  
>   
> + uart\_console\_write(port, s, n, owl\_console\_putchar);   
> }

3）在kernel command line选中我们新增的console

> -CONFIG\_CMDLINE="earlycon=owl\_serial loglevel=8"   
> +CONFIG\_CMDLINE="earlycon=owl\_serial console=ttyS5 loglevel=8"

4）编译并运行，获得如下打印（early console被禁止了，ttyS5被使能了），console移植成功

> [ 0.087281] workingset: timestamp\_bits=60 max\_order=19 bucket\_order=0   
> [ 0.093281] owl\_serial\_init   
> [ 0.096062] owl\_serial e012a000.serial: owl\_serial\_probe   
> [ 0.101343] e012a000.serial: ttyS5 at MMIO 0xe012a000 (irq = 0, base\_baud = 0) is a unknown   
> [ 0.109656] console [ttyS5] enabled   
> [ 0.109656] console [ttyS5] enabled   
> [ 0.116593] bootconsole [owl\_serial0] disabled   
> [ 0.116593] bootconsole [owl\_serial0] disabled  
> [ 0.125468] Failed to find cpu0 device node   
> [ 0.129593] Unable to detect cache hierarchy from DT for CPU 0   
> [ 0.135874] Freeing unused kernel memory: 116K (ffffff80081a0000 - ffffff80081bd000)   
> [ 0.143093] This architecture does not have kernel memory protection.   
> [ 0.149562] Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.   
> [ 0.162593] Kernel Offset: disabled   
> [ 0.166062] Memory Limit: none   
> [ 0.169093] ---[ end Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.

注2：以上过程可参考[3]中的patch文件。

## 5. 参考文档

[1] [X-017-KERNEL-串口驱动开发之uart driver框架](/x_project/serial_driver_porting_2.html)

[2] [X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)

[3] patch文件，[https://github.com/wowotechX/linux/commit/9f4d974605fbc9312333f95a0cd2ae1e4f709941](https://github.com/wowotechX/linux/commit/9f4d974605fbc9312333f95a0cd2ae1e4f709941 "https://github.com/wowotechX/linux/commit/9f4d974605fbc9312333f95a0cd2ae1e4f709941")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/serial_driver_porting_3.html)。
