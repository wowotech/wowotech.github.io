---
title: "X-020-ROOTFS-initramfs的制作和测试"
date: 2016-12-03T11:08:08+08:00
url: "/x_project/simple_initramfs.html"
gid: "360"
emlog_type: "blog"
summary: "\n\t我们在“X-015-KERNEL-ARM \ngeneric timer driver的移植”中移植完ARM generic \ntimer之后，Linux的启动已经走完了内核空间的旅程，即将冲破kernel走向用户空间，有“诗”为证：\n\n\n\t\n\t\t[&nbsp;&nbsp;&nbsp; 0.142156] ---[ end Kernel panic - not syncing: No worki"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["GIC", "initramfs", "randisk", "elf", "rootfs"]
views: 10970
comment_count: 0
aliases:
  - "/x_project/360.html"
  - "/360.html"
---

## 1. 前言

我们在“[X-015-KERNEL-ARM generic timer driver的移植](/x_project/generic_timer_porting.html)”中移植完ARM generic timer之后，Linux的启动已经走完了内核空间的旅程，即将冲破kernel走向用户空间，有“诗”为证：

> [ 0.142156] ---[ end Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.

意思很明显，kernel找不到可执行的init文件，无法继续下去了。还好，基本的串口驱动[1]开发完毕之后，我们可以把魔抓伸向用户空间了。牵涉到用户空间，麻烦就大了，块设备、文件系统、rootfs等等，不是三言两语就能搞定的。不过没关系，我们可以从最简单的ramdisk入手。

因此，本文将以initramfs为例，介绍kernel把CPU的控制权交给用户空间程序的过程。与此同时，本文也是串口驱动[1]和GIC驱动[2]的测试用例（这两个驱动移植完成后，一直没有测试，机会终于来了）。

## 2. 知识汇整

由[1]的介绍可知，当前系统的console为serial console，对应UART5（ttyS5），结合[4]中的描述，Linux kernel在启动的过程中，会打开“/dev/console”设备（该设备其实对应的UART5的driver），并将stdin（0）、stdout（1）、stderr（2）三个文件句柄，和该设备对应。

然后，kernel会执行用户空间的init程序（如/sbin/init），并将上面三个文件句柄继承给init程序。因此，会有如下的结论：

> init程序的stdin（如getchar、scanf等），对应UART5 driver的RX；
>
> init程序的stdout（如printf等），对应UART5 driver的TX。

这就是本文后续描述的理论基础，请大家务必理解。

## 3. initramfs的制作

有关initramfs的概念和介绍，可以参考ooonebook同学写的一篇博文[3]，这里只关注制作步骤。

#### 3.1 编写一个简单的程序，冒充Linux系统的init程序

> cd ~/work/xprj/build   
> touch init.c

该程序很简单，打印一些字符串之后，阻塞在getchar()函数上，每接收一个字符串，就把它打印出来，如下：

> #include< stdio.h>
>
> int main(void)   
> {   
> char ch;   
>   
> printf("Test /sbin/init main....\n");   
> printf("0123456789abcdefghijklmnopqrstuvwxyz\n");   
> printf("ABCDEFGHIJKLMNOPQRSTUVWXYZ9876543210\n");   
>   
> while ((ch = getchar()) != 'q')   
> printf("%c", ch);   
>   
> return 0;   
> }

由第2章的知识汇整可知，printf字符串输出，会经stdout（fd=1）交给serial driver的TX发送出去，而getchar将会读取stdin（fd=0）上的输入数据，这些数据是由serial driver的RX送过来的。

编写完成后，用静态链接的方式，编译生产init文件，留待后面使用：

> pengo@ubuntu:~/work/xprj/build$ ./gcc-linaro-aarch64-linux-gnu-4.8-2013.12\_linux/bin/aarch64-linux-gnu-gcc -static -o init init.c
>
> pengo@ubuntu:~/work/xprj/build$ file init
>
> init: ELF 64-bit LSB executable, version 1 (SYSV), statically linked, for GNU/Linux 3.7.0, not stripped

#### 3.2 将init文件copy到一个目录中，并打包成initramfs的格式

> pengo@ubuntu:~/work/xprj/build$ mkdir out/rootfs/sbin/ -p   
> pengo@ubuntu:~/work/xprj/build$ cp init out/rootfs/sbin/init

打包的脚本如下（具体可参考后面的patch文件）：

> ROOTFS\_OUT\_DIR=$(OUT\_DIR)/rootfs
>
> initramfs:   
> mkdir -p $(OUT\_DIR)   
> cd ${ROOTFS\_OUT\_DIR}; find . | cpio -H newc -o | gzip -9 -n > ${OUT\_DIR}/initramfs.gz

编译并生成initramfs文件的过程如下：

> pengo@ubuntu:~/work/xprj/build$ make initramfs   
> mkdir -p /home/pengo/work/xprj/build/out   
> cd /home/pengo/work/xprj/build/out/rootfs; find . | cpio -H newc -o | gzip -9 -n> /home/pengo/work/xprj/build/out/initramfs.gz  
> 1331 blocks

#### 3.3 修改.its文件[5]，加入上面生成的initramfs文件

具体可参考如下的patch文件（不在详细解释）：

> [https://github.com/wowotechX/build/commit/39d71bf8f922c5da4749ee73ccaa68e5660f808f](https://github.com/wowotechX/build/commit/39d71bf8f922c5da4749ee73ccaa68e5660f808f "https://github.com/wowotechX/build/commit/39d71bf8f922c5da4749ee73ccaa68e5660f808f")

#### 3.4 配置Linux kernel，使其支持RAM filesystem/RAM disk、ELF格式

> make kernel-config
>
> General setup --->   
> [\*] Initial RAM filesystem and RAM disk (initramfs/initrd) support
>
> Userspace binary formats --->   
> [\*] Kernel support for ELF binaries

其中RAM filesystem用于支持initramfs，“ELF binaries”用于支持ELF格式的文件（3.1中编译生产的init文件即为该格式，这也是Linux应用程序的常用格式）。

#### 3.5 修改kernel默认的命令行参数，加入root=、init=等参数

如下：

> +CONFIG\_CMDLINE="earlycon=owl\_serial console=ttyS5 loglevel=8 root=/dev/ram0 init=/sbin/init"

#### 3.6 重新编译kernel并运行

> make kernel initramfs uImage

编译完成后，运行查看效果（u-boot会自动把initramfs image解压并传给kernel）：

> make spl-run   
> …   
> make kernel-run

运行的结果是，init程序可以正确运行，可是printf输出不完整，getchar()输入压根不起作用。不过没关系，慢慢解决就行了。

## 4. 问题汇总以及解决思路

在uart driver中增加一些打印，发现存在如下两个问题：

> 1）GIC无法产生中断。
>
> 2）串口发送时中断有关的处理逻辑不正确。

#### 4.1 GIC无法产生中断

对于该问题，解决方案是：在u-boot中打开对GIC的支持（在头文件中增加GIC有关的定义即可）

注1：该方法只有在u-boot使用了armv8标准low\_level\_init函数时有效，具体可参考[6]。

注2：有关GICD\_BASE、GICC\_BASE的意义，可参考[2]以及u-boot的source code。

> /\* Generic Interrupt Controller Definitions \*/
>
> +#define CONFIG\_GICV2   
> +   
> #define GICD\_BASE (0xe00f1000)   
> #define GICC\_BASE (0xe00f2000)

这样做的原因是：

> ARM64的GIC控制器，有一些特殊的设置，需要在EL3配置。而kernel启动时，会把运行级别切换为EL1[7]，显然无法做这个事情。
>
> 参考u-boot的代码（arch/arm/cpu/armv8/start.S中lowlevel\_init接口），u-boot在切换运行级别之前，做了这些事情：
>
> #if defined(CONFIG\_GICV2) || defined(CONFIG\_GICV3)   
> branch\_if\_slave x0, 1f   
> ldr x0, =GICD\_BASE   
> bl gic\_init\_secure  
> 1:   
> #if defined(CONFIG\_GICV3)   
> ldr x0, =GICR\_BASE   
> bl gic\_init\_secure\_percpu   
> #elif defined(CONFIG\_GICV2)   
> ldr x0, =GICD\_BASE   
> ldr x1, =GICC\_BASE   
> bl gic\_init\_secure\_percpu   
> #endif
>
> 而此时，CPU刚从ROM code执行完毕，也就是说说，ROM code交出控制权的时候，需要确保运行级别为EL3。

#### 4.2 串口发送异常

解决该问题的具体步骤，这里就不再罗列了，可参考如下patch：

> [https://github.com/wowotechX/linux/commit/62cc2deb788f56dc4c0e2a43e308fd1084875d8e](https://github.com/wowotechX/linux/commit/62cc2deb788f56dc4c0e2a43e308fd1084875d8e "https://github.com/wowotechX/linux/commit/62cc2deb788f56dc4c0e2a43e308fd1084875d8e")

有一些串口编程的要点，总结如下（稍后我会更新“[X-018-KERNEL-串口驱动开发之数据收发](/x_project/serial_driver_porting_4.html)[1]”中的流程图）：

1）只要没有数据发送（TX FIFO为空），串口将会一直产生TX中断，这对系统来说是一个灾难，因此串口TX中断的使能是有条件的，具体为：TX FIFO已经满了，TX buffer中还有未发送完成的数据。

> 此时我们需要使能TX中断，当TX FIFO剩余一定的空间之后，产生中断，在中断处理中继续发送。
>
> 除此之外，在任何时候，如果TX buffer已经没有数据了，我们需要把TX中断disable。

2）在串口的中断处理中，要以此对TX、RX分别处理一次，也就是说：

> 只能用if if语句，不能用if else。

3）在串口中断处理中处理RX数据时，在读完RX FIFO之后，需要调用tty\_flip\_buffer\_push，将接收的数据交给上层的line discipline。

#### 4.3 问题解决后，再次测试

已经okay了，结果如下：

> [15:39:26.310] [ 0.188249] This architecture does not have kernel memory protection.   
> [15:39:26.310] Test /sbin/init main....   
> [15:39:26.310] 0123456789abcdefghijklmnopqrstuvwxyz   
> [15:39:26.310] ABCDEFGHIJKLMNOPQRSTUVWXYZ9876543210   
> [15:39:28.220] 123455566   
> [15:39:32.140]   
> [15:39:32.140] 123455566   
> [15:39:32.140]   
> [15:39:32.800]   
> [15:39:33.380] 1212121   
> [15:39:34.320]   
> [15:39:34.320] 1212121   
> [15:39:55.320] q

## 5. 参考文档

[1] [X-019-KERNEL-串口驱动开发之数据收发](/x_project/serial_driver_porting_4.html)

[2] [X-014-KERNEL-ARM GIC driver的移植](/x_project/gic_driver_porting.html)

[3] <http://blog.csdn.net/ooonebook/article/details/52624481>

[4] [Linux TTY framework(3)\_从应用的角度看TTY设备](/tty_framework/application_view.html)

[5] [u-boot FIT image介绍](/u-boot/fit_image_overview.html)

[6] [u-boot启动流程分析(2)\_板级(board)部分](/u-boot/boot_flow_2.html)

[7] [ARM64的启动过程之（一）：内核第一个脚印](/armv8a_arch/arm64_initialize_1.html)

[8] patch文件，`786f2bd, 39d71bf, 29bf568, e2b1555, 62cc2de`

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/simple_initramfs.html)。
