---
title: "显示技术介绍(3)_CRT技术"
date: 2016-01-30T22:18:21+08:00
url: "/display/crt_intro.html"
gid: "261"
emlog_type: "blog"
summary: "CRT（Cathode Rays Tube，阴极射线管）是最原始的电子显示技术，在上世纪被广泛运用于模拟电视（Analog television）系统中。本文将以模拟电视系统为背景，介绍CRT显示技术的原理、特性以及一些关键术语。 众所周知，CRT显示已经逐步被数字显示取代，已有退出历史舞台之势，本文之所以介绍它，原因有三： 1）模拟电视是我们这一代人童年的记忆，美好又神秘。现在回头去看，发觉其中"
author: "wowo"
category: "显示"
category_alias: "display"
tags: ["CRT", "scan", "blank", "unblank", "front", "porch", "back"]
views: 25575
comment_count: 7
aliases:
  - "/display/261.html"
  - "/261.html"
---

#### 1. 前言

CRT（Cathode Rays Tube，阴极射线管）是最原始的电子显示技术，在上世纪被广泛运用于模拟电视（Analog television）系统中。本文将以模拟电视系统为背景，介绍CRT显示技术的原理、特性以及一些关键术语。

众所周知，CRT显示已经逐步被数字显示取代，已有退出历史舞台之势，本文之所以介绍它，原因有三：

> 1）模拟电视是我们这一代人童年的记忆，美好又神秘。现在回头去看，发觉其中的技术是那么的简单、有趣，值得一说。
>
> 2）帮助理解显示时序（video mode，or display timings）。对写过显示驱动的人来说，显示屏的那长长一串的时序相关的参数（xres, yres, hsync len, vsync len, left margin, etc.），足以让自己崩溃。追根溯源，它们产生于CRT技术，现在之所以还存在，很大程度上是CRT的延续，没有太多实质的意义。
>
> 3）现在很多前沿的显示技术，如PDP、FED等，都和CRT的工作机制类似（具体可以参考“[显示技术介绍(2)\_电子显示的前世今生](/display/display_tech_intro.html)”中的介绍）。理解CRT是理解这些新技术的基础。

#### 2. CRT简介

CRT显示技术的本质是：

> 1）电子枪发射电子束，并在加速电场的作用下加速。
>
> 2）电子束轰击荧光物质发光。发光的亮度取决于电子束的速度，即加速电场的强度。
>
> 3）加速电场的强度由输入的视频信号控制，因此可以还原视频。
>
> 4）电子束可以产生直径略小于1mm的光点，在偏转系统的控制下，可以分时点亮屏幕上所有的区域，并利用人眼视觉暂留原理，产生一副完成的画面（人眼看来）。

因此，CRT包含了电子束产生（电子枪）、加速系统、偏转系统、涂有荧光物质的显示屏等基本组件，它们组合在一起，再加一个管壳，就是常说的阴极射线管（CRT）。

#### 3. 模拟电视系统简介

模拟电视系统是一个包含视频信号采集输出、编码、传输、解码、还原显示的系统，其框图如下：

[![模拟电视系统](/content/uploadfile/201601/44dafca396f2613751064c4f7e81d8d420160130141815.gif "模拟电视系统")](/content/uploadfile/201601/fd2d5c0f3d9de5e6c2b56287b036611e20160130141814.gif)

图片1 模拟电视系统

> 模拟电视系统中的显示终端（电视）基本上采用CRT显示，因此也称作CRT电视。一般情况下，CRT电视作为一个整体，包含了RF de-modulation、Analog decoding、CRT display三个部分。

#### 4. 光电转换和电光转换

CRT是把电信号转换为光信号的一种技术，但电信号是怎么来的呢？巧的很，也可以使用类似的技术，如下：

[![电光&光电转换](/content/uploadfile/201601/cdb3b2017cec028e1d49f5e99c2db3c320160130141817.gif "电光&光电转换")](/content/uploadfile/201601/a73ac62dda6cb2da01ed88ae36b0149b20160130141816.gif)

图片2 光电&电光转换

上图描述了基于CRT的模拟电视系统的技术基础：

> 电子束轰击光电靶形成电回路，将光信号转换为电信号，完成光电转换；
>
> 加速后的电子束轰击荧光物质发光，将电信号转换回光信号，完成电光转换。

光电转换的目的是把图像信号转换为电信号，以便于传输、保存，转换后的电信号就是电子显示的源数据。上图左边部分介绍了基于阴极射线的光电转换过程：

> 1）电子枪的阴极产生电子束，并打在一个导电的光电靶上。
>
> 2）光电靶通过一个电阻（RL）和电子枪的阳极连接，打在光电靶上的电子束流经电阻回到电子枪的阳极，从而形成一个电回路。
>
> 3）光电靶本身也有电阻，且随光线强度的改变而改变（可以看做光敏电阻）。因此在光电靶和RL之间会产生随光线变化而变化的电压输出，就是视频信号输出。

光信号转换为电信号后，经过存储、传输、转换后，会以输入信号的形式，控制CRT中加速电场的强度，进而控制荧光屏上荧光物质的发光强度，完成电光转换（电子显示）。

理解了上面光电转换和电光转换的过程之后，我们会产生如下疑问：

> 问题一：一个光电靶只能反映一个点的光线变化，但这显然不够，一个足够大的平面上所有点的光线变化才是有意义的，要怎么做？
>
> 问题二：为什么一定需要电子束来形成电回路，一个简单的导线不也可以达到目的吗？

要回答上面两个问题，我们要进一步理解电子扫描的原理。

#### 5. 电子扫描

首先回答问题二，电子束当然不是必须的，现在普遍使用的数码摄像、数字显示等技术，都不需要电子束的参与，当然，它们不在本文的介绍范围内，就不过多涉及了。因此，我们先分析基于电子束的场景。

对于问题一，怎么得到一个平面上多个点的光线变化呢？机智的工程师们想到了扫描（Scanning）。所谓的扫描，就是同一时刻只处理一个点，如果能够在短时间内（足以欺骗人的眼睛的时间，如40ms）处理完所有的点，就万事大吉了，如下图所示：

[![Raster-scan](/content/uploadfile/201601/beffb29b28e822e8cdb3959f46500ed220160130141820.gif "Raster-scan")](/content/uploadfile/201601/a7cad56af744a5d04b96979f8276d3eb20160130141819.gif)

图片3 Raster scanning

上面图片所描述的电子扫描（也称作光栅扫描，Raster scanning[2]），在模拟电视系统中，既用于图像的采集，也用于图像的显示。可以这样理解：

> 我们可以使用多个光电靶（假设是MxN个）组成一个平面，然后在电子束经过的路径上的水平和垂直方向分别加入合适的磁场，磁场的强度由一个由锯齿波信号控制的线圈（偏转线圈）决定，由于磁场会使电子束偏转，因此就可以控制电子束以从左到右、从上到下的方式，分别打到每一个光电靶上。这个过程就叫做扫描。
>
> 扫描的结果，是将MxN个光电靶所代表的的光信号，分别转换成电信号，并依次输出。这样的一个电信号序列，称作一个图像帧（Frame），接收端（CRT显示器），按照同样的规则，就可以将这样的图像帧还原显示。

关于电子扫描，有很多重要的概念，会在显示有关的驱动编写中用到，下面结合上面图片，一一解释。

**1）扫描线（Scan lines）和分辨率（Resolution）**

对电子扫描而言（这里以图像采集为例），一行中所有光电靶输出的信号实际上是连续信号，这就意味着：

> 一行所包含的光电靶个数，对扫描（或者显示）来说，是不重要的，它只影响光信号采集的精度，也即图像的精细度。甚至，显示端根本不关心采集端到底用了多少个光电靶采集信号（由于是模拟信号，它也无从得知）。这个特征决定在电子扫描的水平方向上，并没有分辨率的概念，整个水平方向上的一行，称作一个扫描线（Scan line）。
>
> 对模拟的CRT显示来说，只需要根据显示器的特性（水平方向有多长），将一行的模拟信号map过去即可。

当每一行扫描结束的时候，电子束需要在水平偏转磁场和垂直偏转磁场的偏转作用下，回到下一行的起点（这个过程称作回扫，下面会介绍），这中间不允许采集信号，因而每一个扫描线之间，是不连续的。也就是说，电子扫描在垂直方向上有分辨率的概念，即多少个扫描线（Scan lines）。

综上所述，在电子扫描中，分辨率可以用Scan lines表示，例如576 lines。

**2）回扫（Horizontal/Vertical retrace）**

电子束从左向右扫描完一行后，需要在水平偏转磁场的作用下快速移回到最左边，并在垂直偏转磁场的作用下，向下偏转一个scan line，以便扫描下一行。同理，电子束从上向下扫描完一帧后，也需要在垂直偏转磁场的作用下快速移回到最左边。因此，水平和垂直两个偏转磁场，实际上是一个周期性的锯齿波，如下：

[![Scanning-pattern](/content/uploadfile/201601/068d6bf77403d94a6d91207be26bf25b20160130141821.gif "Scanning-pattern")](/content/uploadfile/201601/2acb8e3153544c5b217804b83eee67da20160130141820.gif)

图片4 Scanning-pattern

斜率为正的上升期，称作正扫描，电子束将会从左向右（或者从上向下）偏转。斜率为负的下降期，称作回扫（retrace），电子束将会从右向左（或者从下向上）偏转。

由于回扫的过程中不能采集（或者输出）信号，因此需要关闭电子束，称作blank（Horizontal/Vertical balnk）。回扫结束后（回到了最左边或者最右边），需要重新打开电子束，称作unblank。

注1：了解显示驱动（如linux framebuffer）的同学，应该对blank/unblank不陌生，它们的来源正是此处。

**3）前肩（front porch）和后肩（back porch）**

由上面的描述可知，回扫开始的时候需要blank操作，即关闭电子束的发射。在模拟电子的世界里，关闭电子束的发射，其实就是将激发电子束发射的电压从高电平降到一个较低的电平（接近零），但下降的过程是需要时间的（具体原因有多种，这里就不详细分析了），因此：

> 在电平降到一个安全的值之前（电子束不再发射），不能开始回扫。

也就是说，有效的视频信号必须要在回扫开始前结束（即上面图片4中“t2”处），从有效视频信号结束到回扫开始的那一段时间，称作前肩（front porch），这一段时间也是blank操作所需的时间。

另外，回扫也是需要时间的（不用纠结原因，都是老历史了），这一段时间可以用作同步信号。

同样的道理，回扫完成后，unblank操作时，电平从接近零值上升到正常值（可以发射电子束，图片4中的“t1”处）也需要一定的时间，称作后肩（back porch）。在back porch的这一段时间内，视频信号也是无效的。

综上所述：视频信号的有效范围，是图片4中t1到t2的范围，一般称作xres/yres；视频信号的无效范围，是图片4中t2到t1的范围，包括front porch、sync len和back porch（水平或者垂直方向上），一般称作blanking interval（Horizontal/ Vertical blanking interval[3],[4]）。

**4）同步信号（sync pulse）**

由“图片1 模拟电视系统”的描述可知，视频信号在发送之前，需要经过Analog encoding，而编码的过程是不包括前后肩（front/back porch）信息的，因为前后肩的值和具体系统的电路有关，因而不应包含在传输系统中。

但是，从时间轴上看，视频信号是不连续的，每一行的有效信号之后，会有一段horizontal blanking interval，每一帧的有效信号之后，会有一段vertical blanking interval。编码器利用这些空隙时间，传递了一种特殊信号---同步信号（HSYNC和VSYNC，在模拟系统中，该信号以一个高于正常视频电平的高电平脉冲），用于告知接收端每一行以及每一帧视频信号的开始和结束。

#### 6. 显示时序（display timings）和视频模式（videomode）

经过上面章节的介绍，我们对CRT显示技术有了一个基本的了解，并引出了前后肩、同步信号等概念，此时，我们可以回到linux kernel中，看几个数据结构的定义：

```
  1: /* include/video/display_timing.h */
  2: 
  3: struct display_timing {
  4:         struct timing_entry pixelclock;
  5: 
  6:         struct timing_entry hactive;            /* hor. active video *
  7:         struct timing_entry hfront_porch;       /* hor. front porch */
  8:         struct timing_entry hback_porch;        /* hor. back porch */
  9:         struct timing_entry hsync_len;          /* hor. sync len */
 10: 
 11:         struct timing_entry vactive;            /* ver. active video *
 12:         struct timing_entry vfront_porch;       /* ver. front porch */
 13:         struct timing_entry vback_porch;        /* ver. back porch */
 14:         struct timing_entry vsync_len;          /* ver. sync len */
 15: 
 16:         enum display_flags flags;               /* display flags */
 17: };
```

> hactive, hfront\_porch, hback\_porch, hsync\_len/vactive, vfront\_porch, vback\_porch, vsync\_len，是不是已经不陌生了？

再看一下struct videmode和struct fb\_videomode，以及linux下的fbset命令（就不贴代码了，具体可参考include/video/videomode.h、include/linux/fb.h以及Documentation/fb/framebuffer.txt），也都类似，不再难以理解了。

#### 7. 总结

最后，本文对CRT以及模拟电视系统的介绍，只是九牛一毛，很多较为细节的内容，如帧率、隔行扫描（Interlaced scan）、编码、显示制式（PAL/NTSC）等等，都没有涉及。有碍于篇幅和个人精力，就不一一介绍了，如有兴趣，可参考本文后面的一些链接。

#### 8. 参考文献

[1] [https://en.wikipedia.org/wiki/Cathode\_ray\_tube](https://en.wikipedia.org/wiki/Cathode_ray_tube "https://en.wikipedia.org/wiki/Cathode_ray_tube")

[2] <https://en.wikipedia.org/wiki/Raster_scan>

[3] [https://en.wikipedia.org/wiki/Horizontal\_blanking\_interval](https://en.wikipedia.org/wiki/Horizontal_blanking_interval "https://en.wikipedia.org/wiki/Horizontal_blanking_interval")

[4] [https://en.wikipedia.org/wiki/Vertical\_blanking\_interval](https://en.wikipedia.org/wiki/Vertical_blanking_interval "https://en.wikipedia.org/wiki/Vertical_blanking_interval")

[5] [https://en.wikipedia.org/wiki/Analog\_television#Structure\_of\_a\_video\_signal](https://en.wikipedia.org/wiki/Analog_television#Structure_of_a_video_signal "https://en.wikipedia.org/wiki/Analog_television#Structure_of_a_video_signal")

[6] [https://en.wikipedia.org/wiki/Overscan](https://en.wikipedia.org/wiki/Overscan "https://en.wikipedia.org/wiki/Overscan")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/display/crt_intro.html)。*
