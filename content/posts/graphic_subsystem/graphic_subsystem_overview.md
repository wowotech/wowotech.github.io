---
title: "Linux graphic subsytem(1)_概述"
date: 2015-12-17T22:21:48+08:00
url: "/graphic_subsystem/graphic_subsystem_overview.html"
gid: "246"
emlog_type: "blog"
summary: "\r\n\t图形子系统是linux系统中比较复杂的子系统之一：对下，它要管理形态各异的、性能各异的显示相关的器件；对上，它要向应用程序提供易用的、友好的、功能强大的图形用户界面（GUI）。因此，它是linux系统中少有的、和用户空间程序（甚至是用户）息息相关的一个子系统。\r\n\r\n\r\n\t本文是图形子系统分析文章的第一篇，也是提纲挈领的一篇，将会从整体上，对linux图形子系统做一个简单的概述，进而罗列出显"
author: "wowo"
category: "图形子系统"
category_alias: "graphic_subsystem"
tags: ["Linux", "display", "subsystem", "GUI", "Wayland", "SurfaceFlinger", "DRI"]
views: 58255
comment_count: 28
aliases:
  - "/graphic_subsystem/246.html"
  - "/246.html"
---

#### 1. 前言

图形子系统是linux系统中比较复杂的子系统之一：对下，它要管理形态各异的、性能各异的显示相关的器件；对上，它要向应用程序提供易用的、友好的、功能强大的图形用户界面（GUI）。因此，它是linux系统中少有的、和用户空间程序（甚至是用户）息息相关的一个子系统。

本文是图形子系统分析文章的第一篇，也是提纲挈领的一篇，将会从整体上，对linux显示子系统做一个简单的概述，进而罗列出显示子系统的软件构成，后续的文章将会围绕这些软件一一展开分析。

注1：本文所有的描述将以原生linux系统为例（如Ubuntu、Debian等），对其它基于linux的系统（如Android），部分内容会不适用。

注2：本文很多图片都是从网上搜集而来的（很多是从维基百科）。虽然蜗窝的宗旨是用自己的语言表述，尽量自己画图，但是linux图形子系统太复杂了，蜗蜗的理解有限，而老外的图画的实在太好，蜗蜗觉得，再怎么努力，也画不出更好的了，因此本着为读者负责的态度，就直接copy了。

#### 2. 概念介绍

##### 2.1 GUI（Graphical User Interface，图形用户界面）

linux图形子系统的本质，是提供图形化的人机交互（human-computer interaction）界面，也即常说的GUI（Graphical User Interface）。而人机交互的本质，是人脑通过人的输出设备（动作、声音等），控制电脑的输入设备，电脑经过一系列的处理后，经由电脑的输出设备将结果输出，人脑再通过人的输入设备接收电脑的输出，最终实现“人脑<-->电脑”之间的人机交互。下面一幅摘自维基百科的图片（可从[“这里”](https://upload.wikimedia.org/wikipedia/commons/a/a1/Linux_kernel_INPUT_OUPUT_evdev_gem_USB_framebuffer.svg)查看比较清晰的SVG格式的原始图片），对上述过程做了很好的总结：

![Linux_kernel_INPUT_OUPUT_evdev_gem_USB_framebuffer.svg](/content/uploadfile/201512/e8b11450422149.gif "Linux_kernel_INPUT_OUPUT_evdev_gem_USB_framebuffer.svg")

> 该图以一个非常前卫的应用场景----虚拟现实（VR，Virtual Reality）游戏，说明了以图形化为主的人机交互过程：
>
> 1）人脑通过动作、声音（对人脑而言，是output），控制电脑的输入设备，包括键盘、鼠标、操作杆、麦克风、游戏手柄（包含加速度计、陀螺仪等传感器）。
>
> 2）电脑通过输入设备，接收人脑的指令，这些指令经过kernel Input subsystem、Middleware Gesture/Speech recognition等软件的处理，转换成应用程序（Game）可以识别的、有意义的信息。
>
> 3）应用程序（Game）根据输入信息，做出相应的反馈，主要包括图像和声音。对VR游戏而言，可能需要3D rendering，这可以借助openGL及其相应的用户空间driver实现。
>
> 4）应用程序的反馈，经由kernel的Video subsystem（如DRM/KMS）、audio subsystem（如ALSA），输出到电脑的输出设备上，包括显示设备（2D/3D）、扬声器/耳机（3D Positional Audio）、游戏手柄（力的反馈）等。
>
> 5）输出到显示设备上时，可能会经过图形加速模块（Graphics accelerator）。
>
> 注3：图中提到了VR场景的典型帧率（[1280×800@95fps](mailto:1280×800@95fps) for VR），这是一个非常庞大的信息输出，要求图形子系统能10.5ms的时间内，生成并输出一帧，以RGBA的数据格式为例，每秒需要处理的数据量是1280x800x95x4x8=3.11296Gb，压力和挑战是相当大的（更不用提1080P了）。

有关GUI更为详细的解释，请参考：[https://en.wikipedia.org/wiki/Graphical\_user\_interface](https://en.wikipedia.org/wiki/Graphical_user_interface "https://en.wikipedia.org/wiki/Graphical_user_interface")。

##### 2.2 Windowing system（窗口系统）

窗口系统，是GUI的一种（也是当前计算机设备、智能设备广泛使用的一种），以WIMP （windows、icons、menus、pointer) 的形式，提供人机交互接口。Linux系统中有很多窗口系统的实现，如X Window System、Wayland、Android SurfaceFlinger等，虽然形态各异，但思路大致相同，包含如下要点：

> 1）一般都使用client-server架构，server（称作display server，或者windows server、compositor等等）管理所有输入设备，以及用于输出的显示设备。
>
> 2）应用程序作为display server的一个client，在自己窗口（window）中运行，并绘制自己的GUI。
>
> 3）client的绘图请求，都会提交给display server，display server响应并处理这些请求，以一定的规则混合、叠加，最终在有限的输出资源上（屏幕），显示多个应用程序的GUI。
>
> 3）display server和自己的client之间，通过某种类型的通信协议交互，该通信协议通常称作display server protocol。
>
> 4）display server protocol可以是基于网络的，甚至是网络透明的（[network transparent](https://en.wikipedia.org/wiki/Network_transparency)），如X Window System所使用的。也可以是其它类型的，如Android SurfaceFlinger所使用的binder。

有关Windowing system的详细解释，请参考：[https://en.wikipedia.org/wiki/Windowing\_system](https://en.wikipedia.org/wiki/Windowing_system "https://en.wikipedia.org/wiki/Windowing_system")。

##### 2.3 X Window System

似乎终于要进入正题了。

X Window System是Windowing System一种实现，广泛使用于UNIX-like的操作系统上（当然也包括Linux系统），由MIT（Massachusetts Institute of Technology，麻省理工学院）在1984年发布。下图（可从[“这里”](https://upload.wikimedia.org/wikipedia/commons/0/03/X_client_server_example.svg)查看比较清晰的SVG格式的原始图片）是它的典型架构：

[![X_client_server_example](/content/uploadfile/201512/76fa54a98d094de7f36e1181ea12caff20151217141926.png "X_client_server_example")](/content/uploadfile/201512/30348d3c8c496ef98471f2b4bd6fda3020151217141925.png)

> 1）X Window System简称X，或者X11，或者X-Windows。之所以称作X，是因为在字母表中X位于W之后，而W是MIT在X之前所使用的GUI系统。之所以称作X11，是因为在1987年的时候，X Window System已经进化到第11个版本了，后续所有的X，都是基于X11版本发展而来的（变动不是很大）。为了方便，后续我们都以X代指X Window System。
>
> 2）X最初是由X.org（XOrg Foundation）维护，后来基于X11R6发展出来了最初专门给Intel X86架构PC使用的X，称作XFree86（提供X服务，它是自由的，它是基于Intel的PC平台）。而后XFree86发展成为几乎适用于所有类UNIX操作系统的X Window系统，因此在相当长的一段时间里，XFree86也是X的代名词。再后来，从2004年的时候，XFree86不再遵从GPL许可证发行，导致许多发行套件不再使用XFree86，转而使用Xorg，再加上Xorg在X维护工作上又趋于活跃，现在Xorg由成为X的代名词（具体可参考“[http://www.x.org/](http://www.x.org/ "http://www.x.org/")”）。
>
> 3）X设计之初，制定了很多原则，其中一条----"It is as important to decide what a system is not as to decide what it is”，决定了X的“性格”，即：X只提供实现GUI环境的基本框架，如定义protocol、在显示设备上绘制基本的图形单元（点、线、面等等）、和鼠标键盘等输入设备交互、等等。它并没有实现UI设计所需的button、menu、window title-bar styles等元素，而是由第三方的应用程序提供。这就是Unix的哲学：只做我应该做、必须做的事情。这就是这么多年来，X能保持稳定的原因。也是Linux OS界面百花齐放（不统一）的原因，各有利弊吧，后续文章会展开讨论。
>
> 4）X包括X server和X client，它们之间通过X protocol通信。
>
> 5）X server接收X clients的显示请求，并输出到显示设备上，同时，会把输入设备的输入事件，转递给相应的X client。X server一般以daemon进程的形式存在。
>
> 6）X protocol是网络透明（network-transparently）的，也就是说，server和client可以位于同一台机器上的同一个操作系统中，也可以位于不同机器上的不同操作系统中（因此X是跨平台的）。这为远端GUI登录提供了便利，如上面图片所示的运行于remote computer 的terminal emulator，但它却可以被user computer的鼠标键盘控制，以及可以输出到user computer的显示器上。   
> 注4：这种情况下，user computer充当server的角色，remote computer是client，有点别扭，需要仔细品味一下（管理输入设备和显示设备的是server）。
>
> 7）X将protocol封装为命令原语（X command primitives），以库的形式（xlib或者xcb）向client提供接口。X client（即应用程序）利用这些API，可以向X server发起2D（或3D，通过GLX等扩展，后面会介绍）的绘图请求。

有关X更为详细的介绍，请参考：[https://en.wikipedia.org/wiki/X\_Window\_System](https://en.wikipedia.org/wiki/X_Window_System "https://en.wikipedia.org/wiki/X_Window_System")，后续蜗蜗可能会在单独的文章中分析它。

##### 2.4 窗口管理器、GUI工具集、桌面环境及其它

前面讲过，X作为Windowing system中的一种，只提供了实现GUI环境的基本框架，其它的UI设计所需的button、menu、window title-bar styles等基本元素，则是由第三方的应用程序提供。这些应用程序主要包括：窗口管理器（window manager）、GUI工具集（GUI widget toolkit）和桌面环境（desktop environment）。

窗口管理器负责控制应用程序窗口（application windows）的布局和外观，使每个应用程序窗口尽量以统一、一致的方式呈现给用户，如针对X的最简单的窗口管理程序--twm（[Tab Window Manager](https://en.wikipedia.org/wiki/Twm)）。

GUI工具集是Windowing system之上的进一步的封装。还是以X为例，它通过xlib提供给应用程序的API，仅仅可以绘制基本的图形单元（点、线、面等等），这些基本的图形单元，要组合成复杂的应用程序，还有很多很多细碎、繁杂的任务要做。因此，一些特定的操作系统，会在X的基础上，封装出一些更为便利的GUI接口，方便应用程序使用，如Microwindows、GTK+、QT等等。

桌面环境是应用程序级别的封装，通过提供一系列界面一致、操作方式一致的应用程序，使系统以更为友好的方式向用户提供服务。Linux系统比较主流的桌面环境包括GNOME、KDE等等。

##### 2.5 3D渲染、硬件加速、OpenGL及其它

渲染（Render）在电脑绘图中，是指：用软件从模型生成图像的过程。模型是用严格定义的语言或者数据结构对于三维物体的描述，它包括几何、视点、纹理以及照明信息。图像是数字图像或者位图图像。

上面的定义摘录自“[百度百科](http://baike.baidu.com/link?url=isLPUuJ_QLiecmU9BC_Xyh2vd8_4n9DDsRrDfvt3s9NHAmoZ5yxtG7RIOWdYCLJn862qIfigLdewFAvhEqpFI5HAm4nBP7fLRqg15v-7VqK)”，它是着重提及“三维物体”，也就是我们常说的3D渲染。其实我们在GUI编程中习以为常的点、线、矩形等等的绘制，也是渲染的过程中，只不过是2D渲染。2D渲染面临的计算复杂度和性能问题没有3D厉害，因此渲染一般都是指3D渲染。

在计算机中，2D渲染一般是由CPU完成（也可以由专门的硬件模块完成）。3D渲染也可以由CPU完成，但面临性能问题，因此大多数平台都会使用单独硬件模块（GPU或者显卡）负责3D渲染。这种通过特定功能的硬件模块，来处理那些CPU不擅长的事务的方法，称作硬件加速（Hardware acceleration），相应的硬件模块，就是硬件加速模块。

众所周知，硬件设备是多种多样的，为了方便应用程序的开发，需要一个稳定的、最好是跨平台的API，定义渲染有关的行为和动作。OpenGL（Open Graphics Library）就是这类API的一种，也是最为广泛接纳的一种。

虽然OpenGL只是一个API，但由于3D绘图的复杂性，它也是相当的复杂的。不过，归根结底，它的目的有两个：

> 1）对上，屏蔽硬件细节，为应用程序提供相对稳定的、平台无关的3D图像处理API（当然，也可以是2D）。
>
> 2）对下，指引硬件相关的驱动软件，实现3D图像处理相关的功能。

另外，openGL的一个重要特性，是独立于操作系统和窗口系统而存在的，具体可以参考后面软件框架相关的章节。

#### 3. 软件框架

通过第2章的介绍，linux系统中图形有关的软件层次已经呼之欲出，具体如下：

[![display_software_layer](/content/uploadfile/201512/693b0f38e0eedfae1b233f276fb7aad120151217141926.gif "display_software_layer")](/content/uploadfile/201512/5b56a76a97467a71495cd5b764b3ed4720151217141926.gif)

该层次图中大部分的内容，已经在第2章解释过了，这里再补充说明一下：

> 1）该图片没有体现3D渲染、硬件加速等有关的内容，而这些内容却是当下移动互联、智能化等产品比较关注的地方，也是linux平台相对薄弱的环节。后续会在软件框架有关的内容中再着重说明。
>
> 2）从层次结构的角度看，linux图形子系统是比较清晰的，但牵涉到每个层次上的实现的时候，就比较复杂了，因为有太多的选择了，这可归因于“提供机制，而非策略”的Unix软件准则。该准则为类Unix平台软件的多样性、针对性做出了很大的贡献，但在今天这种各类平台趋于整合的大趋势下，过多的实现会导致用户体验的不一致、开发者开发精力分散等弊端，值得我们思考。
>
> 3）虽然图形子系统的层次比较多，但不同的人可能关注的内容不太一样。例如对Linux系统工程师（驱动&中间件）而言，比较关注hardware、kernel和display server这三个层次。而对Application工程师来说，可能更比较关心GUI Toolkits。本文以及后续display subsystem的文章，主要以Linux系统工程师的视角，focus在hardware、kernel和display server（可能包括windows manager）上面。

以X window为例，将hardware、kernel和display server展开如下（可从[“这里”](https://upload.wikimedia.org/wikipedia/commons/c/c2/Linux_Graphics_Stack_2013.svg)查看比较清晰的SVG格式的原始图片）：![Linux_Graphics_Stack_2013.svg](/content/uploadfile/201512/0e651450422536.gif "Linux_Graphics_Stack_2013.svg")

From: [https://upload.wikimedia.org/wikipedia/commons/c/c2/Linux\_Graphics\_Stack\_2013.svg](https://upload.wikimedia.org/wikipedia/commons/c/c2/Linux_Graphics_Stack_2013.svg "https://upload.wikimedia.org/wikipedia/commons/c/c2/Linux_Graphics_Stack_2013.svg")

对于软件架构而言，这张来自维基百科的图片并不是特别合适，因为它包含了太多的细节，从而显得有些杂乱。不过瑕不掩瑜，对本文的描述，也足够了。从向到下，图中包括如下的软件的软件模块：

1）3D-game engine、Applications和Toolkits，应用软件，其中3D-game engine是3D application的一个特例。

2）Display Server

图片给出了两个display server：Wayland compositor和X-Server（X.Org）。X-Server是linux系统在PC时代使用比较广泛的display server，而Wayland compositor则是新设计的，计划在移动时代取代X-Server的一个新的display server。

3）libX/libXCB和libwayland-client

display server提供给Application（或者GUI Toolkits）的、访问server所提供功能的API。libX/libXCB对应X-server，libwayland-client对已Wayland compositor。

4）libGL

libGL是openGL接口的实现，3D application（如这里的3D-game engine）可以直接调用libGL进行3D渲染。

libGL可以是各种不同类型的openGL实现，如openGL（for PC场景）、openGL|ES（for嵌入式场景）、openVG（for Flash、SVG矢量图）。

libGL的实现，既可以是基于软件的，也可以是基于硬件的。其中Mesa 3D是OpenGL的一个开源本的实现，支持3D硬件加速。

5）libDRM和kernel DRM

DRI（Direct Render Infrastructure）的kernel实现，及其library。X-server或者Mesa 3D，可以通过DRI的接口，直接访问底层的图形设备（如GPU等）。

6）KMS（Kernel Mode Set）

一个用于控制显示设备属性的内核driver，如显示分辨率等。直接由X-server控制。

#### 4. 后续工作

本文有点像一个大杂烩，丢进去太多的东西，每个东西又不能细说。觉得说了很多，又觉得什么都没有说。后续蜗蜗将有针对性的，focus在某些点上面，更进一步的分析，思路如下：

> 1）将会把显示框架限定到某个确定的实现上，初步计划是：Wayland client+Wayland compositor+Mesa+DRM+KMS，因为它们之中，除了Mesa之外，其它的都是linux系统中显示有关的比较前沿的技术。当然，最重要的，是比较适合移动端的技术。
>
> 2）通过单独的一篇文章，更详细的分析Wayland+Mesa+DRM+KMS的软件框架，着重分析图像送显、3D渲染、Direct render的过程，以此总结出DRM的功能和工作流程。
>
> 3）之后，把重心拉回kernel部分，主要包括DRM和KMS，当然，也会顺带介绍framebuffer。
>
> 4）kernel部分分析完毕后，回到Wayland，主要关心它的功能、使用方式等等。
>
> 5）其它的，边学、边写、边看吧。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/graphic_subsystem/graphic_subsystem_overview.html)。*
