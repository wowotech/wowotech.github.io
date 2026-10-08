---
title: "Linux电源管理(12)_Hibernate功能"
date: 2014-12-22T11:51:14+08:00
url: "/pm_subsystem/hibernation.html"
gid: "127"
emlog_type: "blog"
summary: "\r\n\t本文简要分析了Linux一种Hibernation实现机制——Swap Suspend的是实现方法。本文会尽量从机制出发，不会深入代码分析，如果您感兴趣，可以参照附件给出的流程图，阅读内核代码，相信您也可以找到其中乐趣。 \r\n\r\n\r\n\tA. Swap Suspend的原因 \r\n\r\n\r\n\tB. 如何实现STF \r\n\r\n\r\n\tC. Swap Suspend的关键 \r\n"
author: "Physh"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Kernel", "hibernation"]
views: 27958
comment_count: 23
aliases:
  - "/pm_subsystem/127.html"
  - "/127.html"
---

出于省电和快速开机的需求, Hibernation经常被应用到Laptop和移动终端上，本文就简单讲讲Hibernation的一种实现实现方法，SWSUSP( Swap Suspend)，其实swsusp从2.6开始就已经被引入到内核版本树中了，所以如果想分析swsusp的代码实现的话，还是挺方便的，只要有有2.6之后的内核代码即可。

本文不会过分深入分析代码，但文章最后会给出hibernation 和 resume的整体流程图。

swsusp是一种STD（Suspend to Disk）/STF（Suspend to Flash）的实现方法，其目的是系统断电之后再次开启时还可以恢复用户现场，从开发的角度切入，为了实现这一目的，系统至少需要保存的关键信息有三类：CPU 状态，Register状态，Memory状态。Swap Suspend中的Swap的含义即指明了该方法如何保存Memory的状态，将Memory保存到Swap分区上，当系统恢复时从Swap分区中读出对应的页面并恢复到Memory中。

那其他两类信息呢？一方面可以另开一块内存空间保留CPU、Register的状态，之后随着Memory一起保存到Swap分区，这种方法之后会讲到，在通过U-boot实现的STF的方法用到了。内核使用了另外一种方法，借用了Kernel CPU Suspend框架，Suspend时让CPU进入Suspend状态，Resume时再从这个状态返回，这样就不同特地去保存CPU、Register状态，不过，话是这样讲，其实本质上还是和第一种方法差不多，CPU Suspend会将Register保存在一个名为sleep\_save\_sp的指针变量指向的一块预留的内核栈空间中，恢复时从中获取寄存器信息。

从简单入手，思考一下通过U-boot如何试下STF/STD？

要从正常运行的系统跳转到U-boot，可以想到的唯一的办法只有Reset了。那Reset之前需要做什么呢？从U-boot的角度来考虑这个问题吧，如果要通过U-boot来实现这个功能，U-boot就有三种状态，1. 冷启动, 2. 热启动(Restore), 3. 制作内存镜像。

这三种状态肯定需要类似于Flag的东西来区别，所以系统Reset之前需要设置Flag来告知U-boot这次Reset的目的是制作内存镜像；另外，U-boot对当前内存使用情况以及Register状态一无所知，不过这些都还不是大问题，因为一般U-boot事先会知道PAGE\_OFFSET，这样就可以通过PAGE\_OFFSET得出swap\_page\_dir以及page\_map[]，寄存器的状态也可以在进入U-boot之后立即保存下来即可。不过，必须提及的是，Reset必须在所有已经都停止之后做，并且Resume回来的时候所有硬件都必须重新初始化。

通过U-boot实现无可避免就是需要多保存内存，当拿到page\_map[]之后，U-boot可以通过各个Page的属性来判断这个页面是否需要保存，当然也可以把整块RAM都保存下来，不过是浪费一点空间。还有一个问题就是U-boot中不能依靠内核Swap机制的接口，所以这些数据往哪儿保存呢？直接往Swap分区写肯定是不行的，因为里边还有系统正常运行时swap out出来页面，要么就要像内核一样有办法获取Swap分区的free block，不行就另想办法，可以往文件里边写，或者弄一个保留分区啥的。

回到正题，Swsusp如何实现STF。

内核对于这个目的的实现就显得比U-boot优雅得多了，与此同时，也复杂的多了，所以说有时粗暴的方法也不见得就是坏办法。swsusp会尝试把最终snapshot image制作的尽可能小，不过这个尺寸用户是可以调控的。

A. Memory Bitmap 机制

看到bitmap估计很多人都会想起内核启动期间用到的boot\_mem，这里的所提及的bitmap和boot\_mem本质是一样，只是在swsusp中不同的bitmap所代表的作用不一，但方法都是通过bit来代表offset，最终对应到一个Page。

swsusp会扫描zone\_list，把不需要保存的page标记起来，这样在制作snapshot image就可以减少image的尺寸。整个过程中用到的bitmap有四张，forbidden\_pages\_map, free\_pages\_map, copy\_bm, orig\_bm，其中不需要保存的page就在forbidden\_pages\_maps中标记，free\_pages\_map的作用用于标识当前系统空闲的PAGE，copy\_bm标记的是临时保存要写如swap分区中的页面，orig\_bm标志系统中所有需要保存的PAGE。

B. Swap 接口

说这个就直接看下面这个图好了，最终往Swap写入之后Swap的状态大致如下图：

![swap_snapshot map.png](/content/uploadfile/201412/1c3d1419220511.png "点击查看原图")

C. Kernel Power Manage机制

之前讲过，swsusp中嵌入Kernel PM从而避免了很多电源管理的冗余操作，其实这样做的好处还可以避免花多很功夫去使得各个驱动恢复到Hibernate之前的状态，所以从各个设备的角度去看，可以认为系统进入一个Suspend状态，只是时间有点长，中途还断电了，不过这些设备都不必操心，因为Restore的时候，它们走标准PM Resume流程又回到之前的状态。

D. Swap Header & swap\_page\_map

在Hibernation的时候，内核会把swap分区的swap\_header换掉，换成自己的swap\_header，这么做的原因是因为Swap 分区在正常使用过程中是按照内存方式使用的，所以如果是冷启动Swap分区肯定更要重置，因此标准的swap\_header没必要记录一些offset什么的，但是restore的时候不一样，拿到Swap分区如何找到snapshot image放在什么地方？这就需要替换的swap\_header来提供了，而swap\_header在swap分区中的位置是不会变的。

还有一个问题就是，Swap中保存snapshot image的page不一定是连续，因此还得有一个方式来映射，这个工作就由swap\_page\_map做了，它本质还是一种bitmap，只是保存的不是内存的页面，而是Swap中的Offset。

（全文完）

如上流程图：

[Hibernation.pdf](/content/uploadfile/201412/bd2e1419231198.pdf)

[Resume Flowchart.pdf](/content/uploadfile/201412/86fb1419231214.pdf)
