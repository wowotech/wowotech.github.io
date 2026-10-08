---
title: "X-021-ROOTFS-基于busybox的最简rootfs的制作"
date: 2016-12-05T22:50:08+08:00
url: "/x_project/simple_busybox.html"
gid: "361"
emlog_type: "blog"
summary: "\r\n\t在前一篇文章[1]中，我们编写并成功运行了一个简单的init程序。于是，“【任务4】启动Linux \r\nkernel到命令行”就成了一个水到渠成的事情。当然，只有一个简单的程序还不够，我们要来点实在的，一个真正的根文件系统。\r\n\r\n\r\n\tLinux系统中制作根文件系统的方法有很多种，基于一个个package一点点编译、利用buildroot、利用busybox、等等，本文将以嵌入式系统中普遍"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["rootfs", "busybox", "inittab", "rcS"]
views: 13682
comment_count: 0
aliases:
  - "/x_project/361.html"
  - "/361.html"
---

## 1. 前言

在前一篇文章[1]中，我们编写并成功运行了一个简单的init程序。于是，“[【任务4】启动Linux kernel到命令行](/forum/67.html)”就成了一个水到渠成的事情。当然，只有一个简单的程序还不够，我们要来点实在的，一个真正的根文件系统。

Linux系统中制作根文件系统的方法有很多种，基于一个个package一点点编译、利用buildroot、利用busybox、等等，本文将以嵌入式系统中普遍使用的busybox为例，介绍制作一个简单的rootfs的方法。

## 2. busybox介绍

嵌入式Linux相关的工程师，对busybox肯定不陌生，百度百科是这样解释的（我不想废话太多，直接copy吧）：

> BusyBox 是一个集成了一百多个最常用linux命令和工具的软件。BusyBox 包含了一些简单的工具，例如ls、cat和echo等等，还包含了一些更大、更复杂的工具，例grep、find、mount以及telnet。有些人将 BusyBox 称为 Linux 工具里的瑞士军刀。简单的说BusyBox就好像是个大工具箱，它集成压缩了 Linux 的许多工具和命令，也包含了 Android 系统的自带的shell。

busybox的官网可参考[2]，为了便于开发，我在“[X Project](/sort/x_project)”的工具目录里面放了一个1.25.1版本的，如下：

> [https://github.com/wowotechX/tools/tree/master/common/busybox-1.25.1](https://github.com/wowotechX/tools/tree/master/common/busybox-1.25.1 "https://github.com/wowotechX/tools/tree/master/common/busybox-1.25.1")

## 3. busybox的配置

#### 3.1 基本配置

和Linux kernel、u-boot等软件类似，busybox也有强大而灵活的配置项，也是通过menuconfig配置。按照“[X Project](/sort/x_project)”的一贯作风，拿到busybox的源代码之后，我们会对它进行简单的配置，并保存一份“[X Project](/sort/x_project)”专用的配置文件，过程如下：

> cd work/xprj/tools/common/busybox-1.25.1/   
> make defconfig #基于busybox的默认配置（包括所有内容）   
> cp .config configs/xprj\_defconfig #将生成的.config文件保存为x project的defconfig文件，以便后续使用   
> make mrproper #最后将文件夹清一下

简单的配置后，需要在x project的编译脚本中（./work/xprj/build/Makefile）加入编译busybox的脚本，内容如下：

> busybox-config:   
> mkdir -p $(BUSYBOX\_OUT\_DIR)   
> cp -f $(BUSYBOX\_DIR)/configs/$(BUSYBOX\_DEFCONFIG) $(BUSYBOX\_OUT\_DIR)/.config   
> make -C $(BUSYBOX\_DIR) O=$(BUSYBOX\_OUT\_DIR) menuconfig   
> cp -f $(BUSYBOX\_OUT\_DIR)/.config $(BUSYBOX\_DIR)/configs/$(BUSYBOX\_DEFCONFIG)
>
> busybox:   
> mkdir -p $(BUSYBOX\_OUT\_DIR) $(ROOTFS\_OUT\_DIR)   
> make -C $(BUSYBOX\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) O=$(BUSYBOX\_OUT\_DIR) $(BUSYBOX\_DEFCONFIG)   
> make -C $(BUSYBOX\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) O=$(BUSYBOX\_OUT\_DIR)   
> make -C $(BUSYBOX\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) O=$(BUSYBOX\_OUT\_DIR) CONFIG\_PREFIX=$(ROOTFS\_OUT\_DIR) install
>
> busybox-clean:   
> rm $(BUSYBOX\_OUT\_DIR) -rf

和编译linux kernel、u-boot的方法一样，我们在单独的文件夹中编译busybox（避免污染原有的source code），这是通过“O”参数实现的，另外几个参数，简单解释如下：

> O，busybox的编译位置（中间文件会在这里生成），这里为./out/busybox。
>
> CROSS\_COMPILE，指定交叉编译器的目录和前缀。
>
> CONFIG\_PREFIX，busybox的安装位置，这里为./out/rootfs，后续会基于该文件夹制作initramfs[1]。

#### 3.2 使用静态链接的方式编译busybox

原理和[1]中编译init程序类似，我们暂时还没有从编译器、C库等位置copy Linux程序运行所必需的动态链接库，因此任何可执行文件只能先以静态链接的形式编译。

需要静态链接的形式编译busybox的话，非常简单，打开它的一个配置项即可，如下：

> make busybox-config
>
> Busybox Settings --->   
> Build Options --->   
> [\*] Build BusyBox as a static binary (no shared libs)

配置完成后会更新“configs/xprj\_defconfig ”文件，具体可参考后面的patch文件。

注1：这一个配置项，是本文唯一需要对busybox改动的地方，强大的开源软件啊！

## 4. 编译并运行

利用3.1中（以及[1]中initramfs）的编译脚本，编译busybox，并打包成initramfs之后，下载到开发板（以Bubblegum-96为例）中执行一把：

> make busybox initramfs uImage #编译
>
> make spl-run #按住ADFU键，运行SPL
>
> make kernel-run #运行u-boot、kernel等

运行成功后，串口上输出如下内容：

> …   
> [ 0.226562] Freeing unused kernel memory: 136K (ffffff80081a8000 - ffffff80081ca000)   
> [ 0.234312] This architecture does not have kernel memory protection.   
> can't run '/etc/init.d/rcS': No such file or directory   
> can't open /dev/tty4: No such file or directory   
> can't open /dev/tty3: No such file or directory   
> can't open /dev/tty2: No such file or directory   
> / #   
> can't open /dev/tty4: No such file or directory   
> can't open /dev/tty3: No such file or directory   
> can't open /dev/tty2: No such file or directory   
> / #   
> / #   
> ls   
> bin dev linuxrc root sbin usr   
> can't open /dev/tty4: No such file or directory   
> can't open /dev/tty3: No such file or directory   
> can't open /dev/tty2: No such file or directory   
> …

看来已经跑起来了（ls等命令已经可用了），但一直在打印“can't …”，没关系，再增加一点东西即可。

## 5. /etc/init.d/rcS和/etc/inittab

#### 5.1 介绍

busybox的正常运行，需要一些必须的配置项，最不可缺少的有两个：

1）/etc/init.d/rcS，/sbin/init成功运行之后，会执行该脚本，我们可以在该脚本中执行后续的初始化操作，如mount文件系统、创建设备节点、等等。

2）/etc/inittab，/etc/init.d/rcS成功执行后，系统就已经处于ready状态，init进程会读取inittab中的配置，决定在哪个设备上启用控制台（当然不止这些）。

为了让第4章出现的命令行可以再正常一些，我们需要在打包rootfs之前，为其创建几个必要的脚本文件，具体如下。

#### 5.2 在script脚本中创建rootfs目录

> cd work/xprj/build/script/   
> mkdir rootfs

#### 5.3 创建rcS文件

busybox的source code中有示例，copy过来就行：

> mkdir rootfs/etc/init.d/ -p   
> cp /home/pengo/work/xprj/tools/common/busybox-1.25.1/examples/bootfloppy/etc/init.d/rcS rootfs/etc/init.d/

查看一下该文件的内容（可以先用着）：

> cat rootfs/etc/init.d/rcS
>
> #! /bin/sh   
> /bin/mount -a

#### 5.4 在rcS中创建两个设备节点/dev/ttyS5和/dev/null

/dev/null是busybox的init进程必须的，/dev/ttyS5是我们的串口设备，需要被用作控制台设备。

> cat rootfs/etc/init.d/rcS
>
> …   
> mkdir /dev -p   
>   
> mknod /dev/ttyS5 c 20 5   
> mknod /dev/ttyS5 c 1 3

#### 5.5 创建inittab

同rcS文件一样，busybox中有示例文件，copy过来：

> cp /home/pengo/work/xprj/tools/common/busybox-1.25.1/examples/bootfloppy/etc/inittab rootfs/etc/

同时，按照examples/inittab的方法，添加ttyS5，如下（具体意义先不用理睬，只要懂115200是什么就行）：

> cat rootfs/etc/inittab
>
> ::sysinit:/etc/init.d/rcS   
> ::respawn:-/bin/sh   
> ::respawn:/sbin/getty -L ttyS5 115200 vt100   
> ::ctrlaltdel:/bin/umount -a -r

#### 5.6 在编译脚本中，添加一个rootfs copy的命令，并在生成initramfs时执行该命令

> -initramfs:   
> +rootfs\_copy:   
> + mkdir -p ${ROOTFS\_OUT\_DIR}   
> + cp -rf ${SCRIPT\_DIR}/rootfs/\* ${ROOTFS\_OUT\_DIR}/   
> +   
> +initramfs: rootfs\_copy  
> mkdir -p $(OUT\_DIR)   
> cd ${ROOTFS\_OUT\_DIR}; find . | cpio -H newc -o | gzip -9 -n > ${OUT\_DIR}/initramfs.gz

okay，按照第4章的方法，再次编译运行，出现如下的打印：

> [ 0.226749] Freeing unused kernel memory: 136K (ffffff80081a8000 - ffffff80081ca000)   
> [ 0.234531] This architecture does not have kernel memory protection.   
> mount: can't read '/etc/fstab': No such file or directory   
> / #   
> / #   
> / # ls   
> ls   
> bin dev etc linuxrc root sbin usr   
> / # ls /dev   
> console null ram ttyS5   
> / # ls bin   
> bin   
> ash dumpkmap kbd\_mode mv setarch   
> base64 echo kill netstat setserial   
> …

成功了（虽然还有一个can’t，暂时不理它就是了）。

## 6. 参考文档

[1] [X-020-ROOTFS-initramfs的制作和测试](/x_project/simple_initramfs.html)

[2] busybox官网，[https://busybox.net/](https://busybox.net/ "https://busybox.net/")

[3] patch文件, [1eec32c](https://github.com/wowotechX/tools/commit/1eec32c3fac3ae66a3d27c3c2678af1a3f20c8ae), `b075163,786f2bd,8205b60,a0654a3`

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/simple_busybox.html)。
