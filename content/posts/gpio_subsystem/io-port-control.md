---
title: "linux内核中的GPIO系统之（1）：软件框架"
date: 2014-07-21T14:40:58+08:00
url: "/gpio_subsystem/io-port-control.html"
gid: "67"
emlog_type: "blog"
summary: "作为一个工作多年的系统工程师，免不了做两件事情：培训新员工和给新员工分配任务。对于那些刚刚从学校出来的学生，一般在开始的时候总是分配一些非 常简单的任务，例如GPIO driver、LED driver。往往CPU datasheet的关于GPIO或者IO ports的章节都是比较简单的，非常适合刚入行的工程师。虽然GPIO子系统相关的硬件比较简单，没有复杂的协议，不过，对于软件抽象而言，其分层次"
author: "linuxer"
category: "GPIO子系统"
category_alias: "gpio_subsystem"
tags: ["GPIO", "软件框架"]
views: 95429
comment_count: 49
aliases:
  - "/gpio_subsystem/67.html"
  - "/67.html"
---

一、前言

作为一个工作多年的系统工程师，免不了做两件事情：培训新员工和给新员工分配任务。对于那些刚刚从学校出来的学生，一般在开始的时候总是分配一些非常简单的任务，例如GPIO driver、LED driver。往往CPU datasheet的关于GPIO或者IO ports的章节都是比较简单的，非常适合刚入行的工程师。虽然GPIO子系统相关的硬件比较简单，没有复杂的协议，不过，对于软件抽象而言，其分层次的软件思想是每个嵌入式软件工程师需要掌握的内容。

我更倾向使用GPIO系统这个名字来代替GPIO driver这个名字，GPIO driver仅仅包含了pin signal状态控制和读取的内容，而GPIO系统包括了pin multiplexing、pin configuration、GPIO control、GPIO interrupt control等内容。本文主要是以3.14内核作为例子，讲述linux kernel中GPIO系统的软件框架。

二、GPIO相关硬件有哪些差异

嵌入式工程师总是要处理各种各样的target board，每个target board上的GPIO总是存在不同，例如：

1、和CPU的连接方式不同

对于ARM的嵌入式硬件平台，SOC本身可以提供大量的IO port，SOC上的GPIO controller是通过SOC的总线（AMBA）连接到CPU的。对于嵌入式系统而言，除了SOC的IO port，一些外设芯片也可能会提供IO port，例如：

（1）有些key controller芯片、codec或者PMU的芯片会提供I/O port

（2）有些专用的IO expander芯片可以扩展16个或者32个GPIO

从硬件角度看，这些IO和SOC提供的那些IO完全不同，CPU和IO expander是通过I2C（也有可能是SPI等其他类型的bus）连接的，在这种情况下，访问这些SOC之外的GPIO需要I2C的操作，而控制SOC上的GPIO只需要写寄存器的操作。不要小看这个不同，写一个SOC memory map的寄存器非常快，但是通过I2C来操作IO就不是那么快了，甚至，如果总线繁忙有可能阻塞当前进程，这种情况下，内核同步机制必须有所区别（如果操作GPIO可能导致sleep，那么同步机制不能采用spinlock）。

2、访问方式不同

SOC片内的GPIO controller和SOC片外的IO expander的访问当然不一样，不过，即便都是SOC片内的GPIO controller，不同的ARM芯片，其访问方式也不完全相同，例如：有些SOC的GPIO controller会提供一个寄存器来控制输出电平。向寄存器写1就是set high，向寄存器写0就是set low。但是有些SOC的GPIO controller会提供两个寄存器来控制输出电平。向其中一个寄存器写一就是set high，向另外一个寄存器写一就是set low。

3、配置方式不同

即便是使用了同样的硬件（例如都使用同样的某款SOC），不同硬件系统上GPIO的配置不同。在一个系统上配置为输入，在另外的系统上可能配置为输出。

4、GPIO特性不同。这些特性包括：

（1）是否能触发中断。对一个SOC而言，并非所有的IO port都支持中断功能，可能某些处理器只有一两组GPIO有中断功能。

（2）如果能够触发中断，那么该GPIO是否能够将CPU从sleep状态唤醒

（3）有些有软件可控的上拉或者下拉电阻的特性，有的GPIO不支持这种特性。在设定为输入的时候，有的GPIO可以设定debouce的算法，有的则不可以。

5、多功能复用

有的GPIO就是单纯的作为一个GPIO出现，有些GPIO有其他的复用的功能。例如IO expander上的GPIO只能是GPIO，但是SOC上的某个GPIO除了做普通的IO pin脚，还可以是SPI上clock信号线。

三、硬件功能分类

ARM based SOC的datasheet中总有一个章节叫做GPIO controller（或者I/O ports）的章节来描述如何配置、使用SOC的引脚。虽然GPIO controller的硬件描述中充满了大量的寄存器的描述，但是这些寄存器的功能大概分成下面三个类别：

1、有些硬件逻辑是和IO port本身的功能设定相关的，我们称这个HW block为pin controller。软件通过设定pin controller这个硬件单元的寄存器可以实现：

（1）引脚功能配置。例如该I/O pin是一个普通的GPIO还是一些特殊功能引脚（例如memeory bank上CS信号）。

（2）引脚特性配置。例如pull-up/down电阻的设定，drive-strength的设定等。

2、如果一组GPIO被配置成SPI，那么这些pin脚被连接到了SPI controller，如果配置成GPIO，那么控制这些引脚的就是GPIO controller。通过访问GPIO controller的寄存器，软件可以：

（1）配置GPIO的方向

（2）如果是输出，可以配置high level或者low level

（3）如果是输入，可以获取GPIO引脚上的电平状态

3、如果一组gpio有中断控制器的功能，虽然控制寄存器在datasheet中的I/O ports章节描述，但是实际上这些GPIO已经被组织成了一个interrupt controller的硬件block，它更像是一个GPIO type的中断控制器，通过访问GPIO type的中断控制器的寄存器，软件可以：

（1）中断的enable和disable（mask和unmask）

（2）触发方式

（3）中断状态清除

四、如何通过软件抽象来掩盖硬件差异

传统的GPIO driver是负责上面三大类的控制，而新的linux kernel中的GPIO subsystem则用三个软件模块来对应上面三类硬件功能：

（1）pin control subsystem。驱动pin controller硬件的软件子系统。

（2）GPIO subsystem。驱动GPIO controller硬件的软件子系统。

（3）GPIO interrupt chip driver。这个模块是作为一个interrupt subsystem中的一个底层硬件驱动模块存在的。本文主要描述前两个软件模块，具体GPIO interrupt chip driver以及interrupt subsystem请参考本站其他相关文档。

1、pin control subsystem block diagram

下图描述了pin control subsystem的模块图：

[![pinctrl](/content/uploadfile/201407/613bd8f3a9ae41cb9511fd4d0bd55c4620140721064054.gif "pinctrl")](/content/uploadfile/201407/eedab24a2cbba83d23e9baa748f6760e20140721064052.gif)

底层的pin controller driver是硬件相关的模组，初始化的时候会向pin control core模块注册pin control设备（通过pinctrl\_register这个bootom level interface）。pin control core模块是一个硬件无关模块，它抽象了所有pin controller的硬件特性，仅仅从用户（各个driver就是pin control subsystem的用户）角度给出了top level的接口函数，这样，各个driver不需要关注pin controller的底层硬件相关的内容。

2、GPIO subsystem block diagram

下图描述了GPIO subsystem的模块图：

[![gpio](/content/uploadfile/201407/490a9605e1250e088b8b2cc6e8201f2020140721064057.gif "gpio")](/content/uploadfile/201407/c33d5c5f19b26bec8dd64ad23197599c20140721064055.gif)

基本上这个软件框架图和pin control subsystem是一样的，其软件抽象的思想也是一样的，当然其内部具体的实现不一样，我们会在后续的文章中描述。

*原创文章，转发请注明出处。蜗窝科技*。[/gpio_subsystem/io-port-control.html](/gpio_subsystem/io-port-control.html)
