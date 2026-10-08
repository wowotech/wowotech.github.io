---
title: "显示技术介绍(2)_电子显示的前世今生"
date: 2015-11-30T22:19:53+08:00
url: "/display/display_tech_intro.html"
gid: "239"
emlog_type: "blog"
summary: "\r\n\t从1907年证实CRT（Cathode Ray \r\nTube）技术可用于电视显示至今，电子显示技术经历了近100年的发展。100年的时间，说长不长，说短也不短；显示技术的发展，说快不快，说慢也不慢。\r\n\r\n\r\n\tCRT技术是最原始的显示技术，但它的生命周期一直持续到2000年后，随着LCD（Liquid Crystal \r\nDisplay）的普及才逐渐退出历史舞台，跨度近90年，这是“不快”"
author: "wowo"
category: "显示"
category_alias: "display"
tags: ["CRT", "LED", "OLED", "Laser", "IMOD"]
views: 19405
comment_count: 2
aliases:
  - "/display/239.html"
  - "/239.html"
---

#### 1. 前言

从1907年证实CRT（Cathode Ray Tube）技术可用于电视显示至今，电子显示技术经历了近100年的发展。100年的时间，说长不长，说短也不短；显示技术的发展，说快不快，说慢也不慢。

CRT技术是最原始的显示技术，但它的生命周期一直持续到2000年后，随着LCD（Liquid Crystal Display）的普及才逐渐退出历史舞台，跨度近90年，这是“不快”的由来。

而最近10年，各种新显示技术，又有层出不穷、快速发展之势，如OLED（Organic light-emitting diode display）、电子墨水（E Ink）、激光电视（Laser TV）、IMOD（Interferometric modulator display）等2D显示技术，如激光显示（Laser display）、光场显示（Light field display）等3D显示技术，这是“不慢”的由来。

蜗蜗本来只打算focus在Linux显示子系统的分析上，不想涉及太多的“题外话”，但专业技术的诱惑力，实在不比linux kernel小。另外，网上真正关注“技术”本身的资料又太少（大多是为了卖电视而写的软文）。因此就在兴趣的驱动下，对显示技术的发展做了一些较深入的了解，顺便在此记录一下。这就是本文以及后续相关文章的由来。

当然，只有兴趣还远远不够，因为任何商业化的技术背后，都有很多基础学科的支撑，数学、物理学、化学、材料学、等等。而离开学校越久远，对这些基础知识越生疏，也只能浅尝辄止了。不过还好，有强大的WJ百科，可以事半功倍，本文大多参考并翻译自下面链接，有兴趣的读者可以自行阅读：

[https://en.wikipedia.org/wiki/History\_of\_display\_technology](https://en.wikipedia.org/wiki/History_of_display_technology "https://en.wikipedia.org/wiki/History_of_display_technology")

[https://en.wikipedia.org/wiki/Display\_device](https://en.wikipedia.org/wiki/Display_device "https://en.wikipedia.org/wiki/Display_device")

#### 2. 电子显示技术汇整

目前为止，电子显示发展出了多种技术，罗列如下（后面再进行一些有针对性的解释）：

> LED（Light-emitting Diode Display），固体二极管在外加电场作用下发光。
>
> OLED（Organic Light-emitting Diode Display），有机发光二极管在外加电场作用下发光。
>
> OLET（Organic Light Emitting Transistor），有机发光晶体管在外加电场作用下发光。
>
> QD-LED（Quantum Dot LED，量子点显示），类似LED、OLED，无机纳米晶体在外加电场的作用下发光。
>
> ELD（Electroluminescent Display，电致发光显示），荧光类半导体，在外加电场作用下发光。
>
> TDEL（Thick-film dielectric electroluminescent technology，无机厚膜电致发光技术），ELD的一种。
>
> LCD（Liquid Crystal Display），LED（或OLED等等）发光后，穿透液晶分子显示。
>
> FLD/FLCD（Ferro liquid display/Ferroelectric Liquid Crystal Display，铁电液晶显示器），液晶显示的一种。
>
> LCOS（Liquid Crystal on Silicon），LED（或OLED等等）发光后，通过硅基液晶反射。背投。
>
> TPD（Telescopic pixel display，伸缩像素显示），一个奇葩的显示技术，基于LCD，借用微型望远镜技术（miniature telescope），在每个液晶像素上增加2个反光镜（其中一个可以在电压的作用下，变成一个凸透镜，以聚焦光速）用于增强LCD背光的透光率，从而可以降低功耗。
>
> CRT（Cathode ray tube display），加热金属阴极后发出电子，轰击屏幕上的荧光粉发光。
>
> PDP（Plasma display panel，等离子显示），类似CRT，惰性气体加压后，产生气体等离子放电现象，放电产生紫外线，紫外线激发屏幕上的荧光粉发光。每一个像素都发光。耗电大。
>
> SED（Surface-conduction electron-emitter display，表面传导电子发射显），类似CRT，碳纳米间隙施加电压产生电子流，然后利用电场使电子逃逸，轰击屏幕上的荧光粉发光。每一个像素都发光。
>
> FED（Field emission display，场致电子发射），类似CRT，在电场自发射阴极（cathode emitter）材料的阴极表面施加强电场，使电子逸出，轰击屏幕的荧光粉发光。
>
> LPD（Laser Phosphor Display，激光磷光荧光体显示），通过激光照射屏幕上的荧光粉发光。
>
> EPD（Electronic Paper Displays），自然光漫射显示。
>
> DLP（Digital Light Procession，数字光处理），先把影像信号经过数字处理，然后再把光投影出来。利用DMD（Digital Micromirror Device）做数字投影。
>
> IMOD（Interferometric modulator display，干涉仪调节器显示技术），自然光漫射显示。两片镜面夹着一个空隙的微小结构，这个空隙决定光线照射显示器时所反射的颜色。
>
> TMOS（Time Multiplexed Optical Shutter，时间多任务光学快门），LED背光系统周期性的产生R、G、B三色光，通过光学快门控制照射到一个像素上R、G、B光线的时间，产生不同的颜色。
>
> DMS（Digital micro shutter，数字微快门），和TMOS类似。
>
> Laser TV（激光电视），和投影机类似，利用半导体泵浦固态激光工作物质，产生红、绿、蓝三种波长的连续激光，经过反射后，投射到屏幕上。背投。
>
> LFD（Light field display，光场显示），重建光场成像（记录光辐射在传播过程中的四维位置和方向的信息）的技术。

#### 3. 思考和理解

##### 3.1 光源的产生

电子显示的本质，是电信号（携带图像信息）转换为光信号，然后被视网膜感知到。因此，光源的产生，是显示过程中最重要的一个环节，同时也是显示技术发展、进化的主要手段，但万变不离其宗，产生光源的技术大概有这么几类：

1）自然光

人眼通过感知物体漫射的自然光，感知物体的存在。这是人类视力的基本原理。EPD、IMOD所使用的光源属于此类，因此这类技术也是最适合人类视力的技术。

2）刺激荧光粉发光

一般使用电子轰击荧光粉发光（CRT、SED、FED属于此类技术）；PDP（等离子显示）比较特殊，使用紫外线刺激荧光粉发光；最直接的是LPD，使用激光刺激荧光粉发光。

3）半导体在外加电场的作用下发光

LED、OLED、OLET、QD-LED、ELD、TDEL等属于此类技术，区别在于半导体的类型。

##### 3.2 电光转换的方法

光源产生后，还需要将表示图像信息的电信号，转换为有明暗变化、颜色变化的光信号，通常有如下的转换方法：

1）直接控制光源

通过电信号的强弱，控制每一个像素点发光的强弱，大部分类LED、类CRT以及Laser TV等显示技术属于此类，不同点是：

> 类LED以及Laser TV等显示技术，电信号的强弱，可以直接控制发光物质发光的强弱；
>
> 类CRT显示技术，电信号的强弱，控制电子、紫外线、激光等刺激源的强弱，进而间接控制荧光粉发光的强弱。

2）光源不变，改变光源的透射率

LCD、FLD/FLCD、LCOS、TPD等显示技术属于此类，一般情况下，使用类LED技术作为背光源，发出固定强度的白色光，穿透液晶分子（或者经过液晶分子反射）发光，通过控制透射率（或者反射率），控制显示的亮度（颜色）。

另外，TMOS（以及DMS）也属于此类，和LCD等技术的区别是，TMOS通过微小的光学快门，控制背光的照射时间，进而控制显示的亮度（颜色）。

3）光源不变，改变光的漫射方式

这一类显示技术比较特殊，是最接近人眼感知世界的方式的技术。代表的有EPD和IMOD两种。

EPD比较直观，其中的一种技术，是将每个像素都封装了带有负电的黑色颗粒和带有正电的白色颗粒，通过改变电荷使不同颜色的颗粒有序排列，从而呈现出黑白分明的可视化效果。

而IMOD则比较前卫，它是通过MEMS（Micro-Electro-Mechanical System，微机电系统）控制两个镜面，改变它们夹着的空隙，进而改变对光的漫射效果。

##### 3.3 直射和反射

之所以强调这一点，是因为人眼对直射光线（例如荧光粉光、LED光）具有较强的不适感，因此显示技术发展的一个方向，是找出使眼睛更舒服的发光方式（反射），其中EPD、LCOS、TMOS、Laser TV等属于此类技术。

##### 3.4 3D显示

Laser TV和LFD是比较适合做3D显示的技术。具体我们在后面的文章中再探讨。

#### 4. 参考文献

[https://en.wikipedia.org/wiki/History\_of\_display\_technology](https://en.wikipedia.org/wiki/History_of_display_technology "https://en.wikipedia.org/wiki/History_of_display_technology")

FLD：[https://en.wikipedia.org/wiki/Ferro\_Liquid\_Display](https://en.wikipedia.org/wiki/Ferro_Liquid_Display "https://en.wikipedia.org/wiki/Ferro_Liquid_Display")

TPD：[http://arstechnica.com/gadgets/2008/07/new-telescopic-pixel-displays-could-outperform-lcd-plasma/](http://arstechnica.com/gadgets/2008/07/new-telescopic-pixel-displays-could-outperform-lcd-plasma/ "http://arstechnica.com/gadgets/2008/07/new-telescopic-pixel-displays-could-outperform-lcd-plasma/")  
[https://en.wikipedia.org/wiki/Telescopic\_pixel\_display](https://en.wikipedia.org/wiki/Telescopic_pixel_display "https://en.wikipedia.org/wiki/Telescopic_pixel_display")

QD-LED：<http://wenku.baidu.com/link?url=DObFHBFKq0aapPjEc7Qxsrs0cmTQfemXYTM5kNu9Wuaz3SrGHQlYE78QPU8mZe7gUcGWCjLSLHl0ZfmbPKEg2rJOIf0_NjgBHfd_B8NTOMy>

LFD：[http://wenku.baidu.com/link?url=Xi5IdJZ\_tRbQwcLbBSJG1bC297YYVwaUBPYFm8IRWRnPeYbsXNn06AKY3rSiPjaCDgecGzXNllsJcFioVmWSoO5qsUoVfL-ayaZYpgKfpf7](http://wenku.baidu.com/link?url=Xi5IdJZ_tRbQwcLbBSJG1bC297YYVwaUBPYFm8IRWRnPeYbsXNn06AKY3rSiPjaCDgecGzXNllsJcFioVmWSoO5qsUoVfL-ayaZYpgKfpf7 "http://wenku.baidu.com/link?url=Xi5IdJZ_tRbQwcLbBSJG1bC297YYVwaUBPYFm8IRWRnPeYbsXNn06AKY3rSiPjaCDgecGzXNllsJcFioVmWSoO5qsUoVfL-ayaZYpgKfpf7")

DMS：[http://www.aptchina.com/zhuanli/11162247/](http://www.aptchina.com/zhuanli/11162247/ "http://www.aptchina.com/zhuanli/11162247/")

TMOS：[https://en.wikipedia.org/wiki/Time-multiplexed\_optical\_shutter](https://en.wikipedia.org/wiki/Time-multiplexed_optical_shutter "https://en.wikipedia.org/wiki/Time-multiplexed_optical_shutter")

IMOD：[http://baike.baidu.com/link?url=uX3-MCJ-He6bg7wqXnpKlHuK8YC6P3hXr7ZNRmTMSPhPVdhNEh-ezxs3BpsVwaNBOrl\_8x7Xw7YivhCeekMFnq](http://baike.baidu.com/link?url=uX3-MCJ-He6bg7wqXnpKlHuK8YC6P3hXr7ZNRmTMSPhPVdhNEh-ezxs3BpsVwaNBOrl_8x7Xw7YivhCeekMFnq "http://baike.baidu.com/link?url=uX3-MCJ-He6bg7wqXnpKlHuK8YC6P3hXr7ZNRmTMSPhPVdhNEh-ezxs3BpsVwaNBOrl_8x7Xw7YivhCeekMFnq")

DLP：[http://baike.baidu.com/link?url=BkV5I8Pjgop8scGWiX2ZbE\_0dyZJzTsjt7A7PuVSzaBWD8N2-Iyl0hF3-h2tvblMjZi3ALeD4o1LkFNl2vvMqq](http://baike.baidu.com/link?url=BkV5I8Pjgop8scGWiX2ZbE_0dyZJzTsjt7A7PuVSzaBWD8N2-Iyl0hF3-h2tvblMjZi3ALeD4o1LkFNl2vvMqq "http://baike.baidu.com/link?url=BkV5I8Pjgop8scGWiX2ZbE_0dyZJzTsjt7A7PuVSzaBWD8N2-Iyl0hF3-h2tvblMjZi3ALeD4o1LkFNl2vvMqq")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/display/display_tech_intro.html)。*
