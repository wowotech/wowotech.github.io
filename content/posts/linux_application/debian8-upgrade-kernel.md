---
title: "Debian8 内核升级实验"
date: 2017-02-27T19:28:35+08:00
url: "/linux_application/debian8-upgrade-kernel.html"
gid: "379"
emlog_type: "blog"
summary: "\r\n\t一直以来，我都是在使用一台ThinkPad T450 ＋ Debian 8的机器来研究内核，Debian 8上缺省的内核版本是3.16，为什么不把内核升级到4.4.6版本上呢？反正现在蜗窝主要分析的也是这个版本的内核？\r\n\r\n\r\n\t本文主要记录了整个升级过程，方便后续重复使用，哈哈，也许哪天要升级到8.8版本的内核呢，到时候可以把这份文档调出来轻松升级。\r\n"
author: "linuxer"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["内核升级"]
views: 14543
comment_count: 1
aliases:
  - "/linux_application/379.html"
  - "/379.html"
---

一、前言

一直以来，我都是在使用一台ThinkPad T450 ＋ Debian 8的机器来研究内核，Debian 8上缺省的内核版本是3.16，为什么不把内核升级到4.4.6版本上呢？反正现在蜗窝主要分析的也是这个版本的内核？

本文主要记录了整个升级过程，方便后续重复使用，哈哈，也许哪天要升级到8.8版本的内核呢，到时候可以把这份文档调出来轻松升级。

二、搞清楚/boot目录下的东西

首先列车/boot目录下的文件如下：

> -rw-r--r-- 1 root root 157726 Feb 29 2016 config-3.16.0-4-amd64   
> drwxr-xr-x 5 root root 4096 Apr 1 2016 grub   
> -rw-r--r-- 1 root root 16873678 Sep 26 16:14 initrd.img-3.16.0-4-amd64   
> -rw-r--r-- 1 root root 2676357 Feb 29 2016 System.map-3.16.0-4-amd64   
> -rw-r--r-- 1 root root 3119232 Feb 29 2016 vmlinuz-3.16.0-4-amd64

vmlinuz-3.16.0-4-amd64是Debian 8使用的kernel image，这个image是如何配置的呢？config-3.16.0-4-amd64就是对应的内核配置文件，System.map-3.16.0-4-amd64是对应的内核符号表，调试内核的时候也许会用到它。initrd.img-3.16.0-4-amd64是内核使用的inital ramdisk image。

OK，收集了这些信息后，我们先理一理思路：要想升级到4.4.6内核，估计必须要提供上面四个文件，配置文件可以沿用，并且用这个配置文件编译出一个新版本的内核image，initrd image有点麻烦，可以考虑沿用，也可以看看是否可以生成一个。符号表文件最简单，编译好4.4.6内核自然就有了。搞定！

三、编译4.4内核

1、准备好4.4.6的源代码

去kernel.org上去下载一个linux-4.4.6.tar.xz，然后解压在自己的工作目录，例如：/home/linuxer/work/linux-4.4.6/。

> xd –d linux-4.4.6.tar.xz
>
> tar –xf linux-4.4.6.tar

2、准备好内核配置文件

自己生成一个配置文件比较费事，借用当前kernel的配置文件是一个不错的主意。

> cd /home/linuxer/work/linux-4.4.6
>
> cp /boot/config-3.16.0-4-amd64 ./.config

3、配置内核

> make olddefconfig

从3.16到4.4，内核的配置项一定会有变化，因此使用旧的内核配置文件存在这样的问题：4.4内核中新的配置项如何选择？如果你的内心足够强大，可以考虑使用make oldconfig，这样，那些新的配置项就可以逐一列出了并请你进行配置。当然，我是没有那么多耐心了，直接使用make olddefconfig，让那些新增加的配置项选择default值吧。

4、生成内核包

> make clean
>
> make deb-pkg

这条命令是用来编译kernel package的。输完该命令后，我建议你可以外出走走，上个厕所，喝杯茶，考虑一下诗和远方什么的，反正随后的一段时间，你的计算机屏幕只是有一行行的字符不断的翻滚而已。当一切归于平静的时候，在kernel source目录的上一级目录可以看到不少的\*.deb的包文件，当然，最重要的就是那个linux-image-4.4.6\_4.4.6-2\_amd64.deb，这个是内核安装包。

四、安装内核包

下面的命令用来安装内核包：

> dpkg -i linux-image-4.4.6\_4.4.6-2\_amd64.deb

作为一个有情怀的工程师，我们当然想知道到底安装了哪些文件，这个信息其实可以从/var/lib/dpkg/info/linux-image-4.4.6.list文件中得到，我们简单整理如下：

（1）/boot目录下的内核镜像（vmlinuz-4.4.6）、内核配置文件（config-4.4.6）和内核符号（System.map-4.4.6）

（2）内核的模块（/lib/modules/4.4.6/\*）

（3）一些内核安装相关的处理脚本（/etc/kernel/\*）。主要是和initrd image以及grub更新相关的工作。通过这些脚本生成了/boot目录下的initrd.img-4.4.6文件（哈哈，initrd image的问题解决了）并且修改了/boot/grub/menu.lst文件。

五、加载内核

很遗憾，安装内核package之后重启系统，一切都没有什么变化，仍然是旧的内核，稍微看了看网上的文章，似乎是和grub的配置相关。升级内核这事以前也做过，对于grub而言，修改menu.lst就OK了，现在的grub2似乎变化了，其配置文件是grub.cfg，而且建议不要手工修改，好吧，看来还是要更新grub的知识啊。

grub的配置文件包括：

（1）/boot/grub/grub.cfg

（2）/etc/grub.d/

（3）/etc/default/grub

有一个能够自动生成配置文件的命令grub-mkconfig，我们可以用这个命令来生成配置文件：

> grub-mkconfig –o /boot/grub/grub.cfg

执行完该命令后，系统会扫描boot目录的内容，以及etc目录下的配置文件，最终生成一个可以使用的grub.cfg文件。OK，现在可以重启享受4.4.6内核吧。

*原创文章，转发请注明出处。蜗窝科技*
