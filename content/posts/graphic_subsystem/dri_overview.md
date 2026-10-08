---
title: "Linux graphic subsystem(2)_DRI介绍"
date: 2015-12-27T22:02:31+08:00
url: "/graphic_subsystem/dri_overview.html"
gid: "249"
emlog_type: "blog"
summary: "\r\n\t上篇文章（Linux \r\ngraphic subsytem(1)_概述）介绍了linux图形子系统基本的软件框架，以及GUI、Windowing \r\nsystem、3D渲染等基本概念。文中提到了linux DRI（Direct Render \r\nInfrastructure）框架，但限于篇幅，没有过多介绍。\r\n\r\n\r\n\t蜗蜗觉得，DRI在当前（或者说将来）的linux图形子系统中，有着举足轻"
author: "wowo"
category: "图形子系统"
category_alias: "graphic_subsystem"
tags: ["DRI", "drm", "kms", "rendering"]
views: 67134
comment_count: 28
aliases:
  - "/graphic_subsystem/249.html"
  - "/249.html"
---

#### 1. 前言

上篇文章（[Linux graphic subsytem(1)\_概述](/graphic_subsystem/graphic_subsystem_overview.html)）介绍了linux图形子系统基本的软件框架，以及GUI、Windowing system、3D渲染等基本概念。文中提到了linux DRI（Direct Render Infrastructure）框架，但限于篇幅，没有过多介绍。

蜗蜗觉得，DRI在当前（或者说将来）的linux图形子系统中，有着举足轻重的地位，甚至可以说是新的linux图形框架核心思想的体现。本文将基于linux图形框架的发展历程，从Why、What和How三个角度，介绍DRI框架。

#### 2. 为什么需要DRI

在GUI环境中，一个Application想要将自身的UI界面呈现给用户，需要2个步骤：

1）根据实际情况，将UI绘制出来，以一定的格式，保存在buffer中。该过程就是常说的“Rendering”。

> 不知道为什么，wowo一直觉得“Render”这个英文单词太专业、太抽象了，理解起来有些困难。时间久了，也就不再执著了，看到它时，就想象一下内存中的图像数据（RGB或YUV格式），Rendering就是生成它们的过程。
>
> 通常来说，Rendering有多种表现形式，但可归结为如下几类：
>
> a）2D的点、线、面等绘图，例如，“通过一个for循环，生成一个大小为640x480、格式为RGB888、填充颜色为红色的矩形框”，就是一个2D rendering的例子。
>
> b）3D渲染。该过程牵涉比较复杂的专业知识，这里先不举例了。
>
> c）图片、视频等多媒体解码。
>
> d）字体渲染，例如直接从字库中抽出。

2）将保存在buffer中的UI数据，显示在display device上。该过程一般称作“送显”。

然后问题就来了：这两个步骤中，display server要承担什么样的角色？回答这个问题之前，我们需要知道这样的一个理念：

> 在操作系统中，Application不应该直接访问硬件，通常的软件框架是（从上到下）：Application<---->Service<---->Driver<---->Hardware。这样考虑的原因主要有二：安全性和共享硬件资源（例如显示设备只有一个，却有多个应用想要显示）。

对稍微有经验的软件开发人员（特别是系统工程师和驱动工程师）来说，这种理念就像杀人偿命、欠债还钱一样天经地义。但直到X server+3D出现之后，一切都不好了。因为X server大喊的着：“让我来！”，给出了这样的框架：

[![x_window_indirect_render](/content/uploadfile/201512/23cefbd968ef1aadb072ab5b21139e5c20151227140230.gif "x_window_indirect_render")](/content/uploadfile/201512/9682677f88a22d926db1d8c7a0bd2a0c20151227140230.gif)

> 先不考虑上面的GLX、Utah GLX等术语，我们只需要理解一点即可：
>
> 基于OpenGL的3D program需要进行3D rendering的时候，需要通过X server的一个扩展（GLX），请求X server帮忙处理。X server再通过底层的driver（位于用户空间），通过kernel，访问硬件（如GPU）。
>
> 其它普通的2D rendering，如2D绘图、字体等，则直接请求X server帮忙完成。

看着不错哦，完全满足上面的理念。但计算机游戏、图形设备硬件等开发人员不乐意了：请让我们直接访问硬件！因为很多高性能的图形设备，要求相应的应用程序直接访问硬件，才能实现性能最优[1]。

好像每个人都是对的，怎么办？妥协的结果是，为3D Rendering另起炉灶，给出一个直接访问硬件的框架，DRI就应运而生了，如下：

[![x_window_direct_render](/content/uploadfile/201512/7510566f6c5231cea11ccbe801d5906320151227140231.gif "x_window_direct_render")](/content/uploadfile/201512/f78202e2a8976d6f7be95da0419c590020151227140230.gif)

上面好像讲的都是Rendering有关的内容，那送显呢？还是由display server统一处理比较好，因为显示设备是有限的，多个应用程序的多个界面都要争取这有限的资源，server会统一管理、叠加并显示到屏幕上。而这里叠加的过程，通常称作合成（Compositor），后续文章会重点说明。

#### 3. 软件架构

DRI是因3D而生，但它却不仅仅是为3D而存在，这背后涉及了最近Linux图形系统设计思路的转变，即：

> 从以前的：X serve是宇宙的中心，其它的接口都要和我对话。
>
> 转变为：Linux kernel及其组件为中心，X server（如Wayland compositor等）只是角落里的一员，可有可无。

最终，基于DRI的linux图形系统如下（参考自[4][5]）：

[![Direct_Rendering_Infrastructure](/content/uploadfile/201512/123fbec41e5f753653f5e6e2825b884f20151227140231.gif "Direct_Rendering_Infrastructure")](/content/uploadfile/201512/f4d05349d9d85543ebbdadf056dddba920151227140231.gif)

该框架以基于Wayland的Windowing system为例，描述了linux graphic系统在DRI框架下，通过两条路径（DRM和KMS），分别实现Rendering和送显两个显示步骤。从应用的角度，显示流程是：

1）Application（如3D game）根据用户动作，需要重绘界面，此时它会通过OpenGL|ES、EGL等接口，将一系列的绘图请求，提交给GPU。

> a）OpenGL|ES、EGL的实现，可以有多种形式，这里以Mesa 3D为例，所有的3D rendering请求，都会经过该软件库，它会根据实际情况，通过硬件或者软件的方式，响应Application的rendering请求。
>
> b）当系统存在基于DRI的硬件rendering机制时，Mesa 3D会通过libGL-meas-DRI，调用DRI提供的rendering功能。
>
> c）libGL-meas-DRI会调用libdrm，libdrm会通过ioctl调用kernel态的DRI驱动，这里称作DRM（Direct Rendering Module）。
>
> d）kernel的DRM模块，最终通过GPU完成rendering动作。

2）GPU绘制完成后，将rendering的结果返回给Application。

> rendering的结果是以image buffer的形式返回给应用程序。

3）Application将这些绘制完成的图像buffer（可能不知一个）送给Wayland compositor，Wayland compositor会控制硬件，将buffer显示到屏幕上。

> Wayland compositor会搜集系统Applications送来的所有image buffers，并处理buffer在屏幕上的坐标、叠加方式后，直接通过ioctl，交给kernel KMS（kernel mode setting）模块，该模块会控制显示控制器将图像显示到具体的显示设备上。

#### 4. DRM和KMS

DRM是Direct Rendering Module的缩写，是DRI框架在kernel中的实现，负责管理GPU（或显卡，graphics card）及相应的graphics memory，主要功能有二：

1）统一管理、调度多个应用程序向显卡发送的命令请求，可以类比为管理CPU资源的进程管理（process management）模块。

2）统一管理显示有关的memory（memory可以是GPU专用的，也可以是system ram划给GPU的，后一种方法在嵌入式系统比较常用），该功能由GEM（Graphics Execution Manager）模块实现，主要包括：

> a） 允许用户空间程序创建、管理、销毁video memory对象（称作“"GEM objects”，以handle为句柄）。
>
> b）允许不同用户空间程序共享同一个"GEM objects”（需要将不唯一的handle转换为同一个driver唯一的GEM name，后续使用dma buf）。
>
> c）处理CPU和GPU之间内存一致性的问题。
>
> d）video memory都在kernel管理，便于给到display controller进行送显（Application只需要把句柄通过Wayland Compositor递给kernel即可，kernel会自行获取memory及其内容）。

KMS是Kernel Mode Setting的缩写，也称作Atomic KMS，它是一个在linux 4.2版本的kernel上，才最终定性的技术。从字面意义上理解，它要实现的功能比较简单，即：显示模式（display mode）的设置，包括屏幕分辨率（resolution）、颜色深的（color depth）、屏幕刷新率（refresh rate）等等。一般来说，是通过控制display controller的来实现上述功能的。

也许大家会有疑问：这些功能和DRI有什么关系？说实话，关系不大，之所以要在DRI框架里面提及KMS，完全是历史原因，导致KMS的代码，放到DRM中实现了。目前的kernel版本（如4.2之后），KMS和DRM基本上没有什么逻辑耦合（除了代码位于相同目录，以及通过相同的设备节点提供ioctl之外），可以当做独立模块看待。

继续上面的话题，只是简单的display mode设置的话，代码实现不复杂吧？还真不一定！相反，KMS有关的技术背景、软件实现等，是相当复杂的，因此也就不能三言两语说得清，我会在单独的文章中重点分析KMS。

#### 5. 参考文档

[1]: [https://en.wikipedia.org/wiki/Direct\_Rendering\_Infrastructure](https://en.wikipedia.org/wiki/Direct_Rendering_Infrastructure "https://en.wikipedia.org/wiki/Direct_Rendering_Infrastructure")

[2]: [https://en.wikipedia.org/wiki/Wayland\_(display\_server\_protocol)](https://en.wikipedia.org/wiki/Wayland_(display_server_protocol) "https://en.wikipedia.org/wiki/Wayland_(display_server_protocol)")

[3]: <http://wayland.freedesktop.org/architecture.html>

[4]: [Linux\_kernel\_and\_daemons\_with\_exclusive\_access.svg](https://en.wikipedia.org/wiki/Direct_Rendering_Manager#/media/File:Linux_kernel_and_daemons_with_exclusive_access.svg)

[5]: [Wayland\_display\_server\_protocol.svg](https://upload.wikimedia.org/wikipedia/commons/a/a7/Wayland_display_server_protocol.svg "https://upload.wikimedia.org/wikipedia/commons/a/a7/Wayland_display_server_protocol.svg")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/graphic_subsystem/dri_overview.html)。*
