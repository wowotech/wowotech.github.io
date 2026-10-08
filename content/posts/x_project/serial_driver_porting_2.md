---
title: "X-017-KERNEL-串口驱动开发之uart driver框架"
date: 2016-11-16T22:09:48+08:00
url: "/x_project/serial_driver_porting_2.html"
gid: "354"
emlog_type: "blog"
summary: "\r\n\t本文是“X \r\nProject”串口驱动开发的第二篇，将以“bubblegum-96”开发板为例，介绍在linux serial \r\nframework的框架下，编写串口driver以及console driver的方法和步骤（暂不涉及实现细节）。\r\n\r\n\r\n\t注1：有关串口、TTY、console等概念，可参考本站“TTY子系统[1]”的文章。Linux serial \r\nframewor"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "Kernel", "driver", "framework", "serial", "console", "uart_driver"]
views: 14278
comment_count: 2
aliases:
  - "/x_project/354.html"
  - "/354.html"
---

## 1. 前言

本文是“[X Project](/sort/x_project)”串口驱动开发的第二篇，将以“bubblegum-96”开发板为例，介绍在linux serial framework的框架下，编写串口driver以及console driver的方法和步骤（暂不涉及实现细节）。

注1：有关串口、TTY、console等概念，可参考本站“TTY子系统[1]”的文章。Linux serial framework的分析，会在后续的文档中补充（这里故意颠倒，以便让大家理解kernel framework的妙处）。

## 2. 硬件说明

我们在前面“u-boot串口驱动移植[2]”以及"linux serial early console移植[3]”的时候，主要以“bubblegum-96”开发板的UART5为例。为了简单，本文也基于UART5，并做到和其它串口兼容。有关“bubblegum-96”开发板UART5的硬件介绍，可以参考[2]，这里不再详细说明了。

## 3. 串口驱动的移植步骤

#### 3.1 定义并注册uart driver

在linux serial framework中，uart driver是一个平行于platform driver的概念，用于驱动“虚拟”的“串口”设备。举例来说：

> 假如一个soc中有5个串口控制器（也可称作uart控制器，后面我们不再区分），每个uart控制器都可引出一个串口（uart port）。那么：
>
> 每个uart控制器，都是一个platform device，由[5]中介绍的dts文件的一个node描述。而这5个platform device，可由同一个driver驱动，即[5]介绍的platform driver。
>
> 相对于uart控制器实实在在的存在，我们更为熟悉的串口（uart port），则是虚拟的设备，它们由“struct uart\_port”描述（后面会介绍），并在platform driver的probe接口中，注册到kernel。它们可由同一个driver驱动，即这里所说的uart driver。

uart driver一般长这个样子（AAA和BBB的含义可参考[5]）：

> #define aaa\_bbb\_MAXIMUM 5   
>   
> static struct uart\_driver AAA\_BBB\_driver = {   
> .owner = THIS\_MODULE,   
> .driver\_name = "AAA\_BBB",   
> .dev\_name = "ttyS",   
> .cons = NULL,   
> .nr = aaa\_bbb\_MAXIMUM,   
> };

其中.cons表示该driver对应的console driver，第4章会补充介绍。.nr表示该uart driver最大支持的uart port个数，根据硬件情况，我们这里定义为5。

uart driver的注册和注销和[5]中介绍的platform driver一样，具体可参考后面的patch文件。

#### 3.2 注册uart port

前面提到过，platform device代表uart控制器，是实体抽象。对应的，uart port代表“串口”，是虚拟抽象。因此，我们需要在platform device probe的时候（platform driver的probe接口），动态分配并注册一个uart port（struct uart\_port）。

由于在后续的串口操作中，都是以uart port指针为对象，所以在通常情况下，为了保存一些自定义的信息，我们会定义一个包含struct uart\_port的数据结构----struct AAA\_uart\_port，如下：

> struct AAA\_uart\_port {   
> struct uart\_port port;
>
> /\* others, TODO \*/   
> };

在probe的时候，会分配struct AAA\_uart\_port类型的指针，然后初始化并注册其中的port变量（这是driver开发的惯用伎俩，大家慢慢就会熟悉），例如：

> struct AAA\_uart\_port \*Aup;   
> struct uart\_port \*port;
>
> Aup = devm\_kzalloc(&pdev->dev, sizeof(\*Aup), GFP\_KERNEL);   
> if (Aup == NULL) {   
> dev\_err(&pdev->dev, "Failed to allocate memory for Aup\n");   
> return -ENOMEM;   
> }   
> platform\_set\_drvdata(pdev, Aup);   
> port = &Aup->port;
>
> port->dev = &pdev->dev;   
> port->type = PORT\_AAA;   
> port->ops = &AAA\_uart\_ops;

注2：这里使用devm\_kzalloc，有关devm\_xxx的说明，可参考[6]。另外我们会调用platform\_set\_drvdata将新申请的Aup指针保持在pdev的drvdata中，以便后续需要使用的时候再取出（例如remove的时候），这也是driver开发的惯用伎俩。

struct uart\_port结构在抽象一个虚拟的“串口”的同时，也保存了该“串口”的一些常用属性，我们需要在probe的时候将这些属性保存在新申请的指针中，包括：

> port->dev，对应的struct device指针；
>
> port->type，该串口的类型，是以PORT\_为前缀的一个宏定义，大家可以根据需要在include/uapi/linux/serial\_core.h中定义；
>
> port->ops，该串口的操作函数集，后面会介绍；
>
> port->iotype，该串口的IO类型，我们常用的通过寄存器访问的uart控制器，选用UPIO\_MEM32即可；
>
> port->membase，对应MEM类型的串口，保持它的寄存器基址，一般是从DTS中解析得到的；
>
> port->irq，该串口对应的中断号， 一般是从DTS中解析得到的；
>
> port->line，该串口的编号，和串口字符设备的次设备号等有关，后面文章会重点介绍；
>
> 等等。

本文先定义一些必要的，其它的会随着功能的完善，逐步添加，具体可参考后面的patch文件[8]。

初始化完之后，直接调用uart\_add\_one\_port接口，将该port添加到kernel serial core即可，如下（第一个参数为上面3.1注册的uart driver指针）：

> ret = uart\_add\_one\_port(&AAA\_BBB\_driver, port);   
> if (ret < 0) {   
> dev\_err(&pdev->dev, "Failed to add uart port, err %d\n", ret);   
> return ret;   
> }

#### 3.3 定义并实现uart ops

struct uart\_ops结构包含了各式各样的uart端口的操作函数，需要在添加uart port的时候提供。开始移植的时候，我们可以只实现部分接口（暂时留空都可以），至少应包括：

> static struct uart\_ops AAA\_uart\_ops = {   
> .startup = AAA\_BBB\_startup,   
> .shutdown = AAA\_BBB\_shutdown,   
> .start\_tx = AAA\_BBB\_start\_tx,   
> .stop\_tx = AAA\_BBB\_stop\_tx,   
> .stop\_rx = AAA\_BBB\_stop\_rx,   
> .tx\_empty = AAA\_BBB\_tx\_empty,   
> .set\_mctrl = AAA\_BBB\_set\_mctrl,   
> .set\_termios = AAA\_BBB\_set\_termios,   
> };

有关这些操作函数的具体含义，我会在下一篇文章中介绍。

## 4. console驱动的移植步骤

在嵌入式开发的过程中，我们通常会从SOC上众多串口中选择一个，当作console设备，以方便开发和调试。在Linux serial framework的框架下，编写一个console驱动是非常简单的。步骤如下：

1）定义struct console变量

有关struct console结构的描述可参考[7]，下面是一个例子：

> static struct console AAA\_console = {   
> .name = "ttyS",   
> .write = AAA\_console\_write,   
> .device = uart\_console\_device,   
> .setup = AAA\_console\_setup,   
> .flags = CON\_PRINTBUFFER,   
> .index = -1,   
> .data = &AAA\_BBB\_driver,   
> };

重点字段的解释如下：

> .name字段决定console的名称，command line传入的时候，需要和该名称匹配，例如“console=ttyS0”；
>
> .index用来指定该console使用哪一个uart port（对应3.2小节中的port->line），这里使用-1，kernel会自动选择第一个uart port。后面有需要的时候我们再改；
>
> .data可以用来保存console的私有数据，这里我们把struct uart\_driver指针保存下来，后面有用；
>
> .setup和.write是两个需要实现的回调函数，我们可以先留空，具体请参考[8]中的patch。

2）将console变量的指针保存在struct uart\_driver变量的.cons字段中，如下：

> static struct console AAA\_console;
>
> static struct uart\_driver AAA\_BBB\_driver = {   
> …   
> .cons = &AAA\_console,   
> …   
> };

3）OK，移植完成。当我们执行3.2小节所介绍的add port的时候，serial core会自动比较uart driver---->cons---->index和uart port---->line，如果匹配，则调用register\_console帮忙注册console驱动。

## 5. 参考文档

[1] [Linux kernel TTY子系统](/sort/tty_framework)

[2] [X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)

[3] [X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)

[4] Documentation/serial/driver

[5] [X-016-KERNEL-串口驱动开发之驱动框架](/x_project/serial_driver_porting_1.html)

[6] [Linux设备模型(9)\_device resource management](/device_model/device_resource_management.html)

[7] [Linux TTY framework(5)\_System console driver](/tty_framework/system_console_driver.html)

[8] 和本文对应的patch文件，[https://github.com/wowotechX/linux/commit/d072d177c9a88e57eb7c5f18c424b96f0ce6d2d5](https://github.com/wowotechX/linux/commit/d072d177c9a88e57eb7c5f18c424b96f0ce6d2d5 "https://github.com/wowotechX/linux/commit/d072d177c9a88e57eb7c5f18c424b96f0ce6d2d5")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/serial_driver_porting_2.html)。
