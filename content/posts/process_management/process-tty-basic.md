---
title: "进程管理和终端驱动：基本概念"
date: 2016-10-28T18:56:20+08:00
url: "/process_management/process-tty-basic.html"
gid: "345"
emlog_type: "blog"
summary: "对于任何一种OS，终端部分的内容总是令人非常的痛苦和沮丧，GNU/linux也是如此。究其原因主要有两个，一是终端驱动和终端相关的系统软件承载了太多的内容：各种虚拟终端、\r\n伪终端、串口通信、modem、printer等。其次可能是终端和信号处理、进程关系等耦合在一起加大了理解终端驱动的难度。本文的目标是希望能够理清这些内容。"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["process", "tty", "session", "group"]
views: 22206
comment_count: 10
aliases:
  - "/process_management/345.html"
  - "/345.html"
---

一、前言

对于任何一种OS，终端部分的内容总是令人非常的痛苦和沮丧，GNU/linux也是如此。究其原因主要有两个，一是终端驱动和终端相关的系统软件承载了太多的内容：各种虚拟终端、 伪终端、串口通信、modem、printer等。其次可能是终端和信号处理、进程关系等耦合在一起加大了理解终端驱动的难度。本文的目标是希望能够理清这些内容。

在第二章，本文会简单介绍终端的一些基础知识，这些知识在wowo的[终端基本概念](/tty_framework/tty_concept.html)文档中也有描述，我这里也重复一次，加深印象（呵呵，其实这一章的内容一年前就写了，后来暂停了，这次重新组织一下，发表出来）。随后的第三章主要描述的是和进程管理相关的TTY（终端）的一些基础知识，希望能够帮助广大人民群众理解进程和终端驱动之间的交互关系。主要的概念包括：session、前台进程组、controlling terminal、Job control等。最后一章是结合实际的应用场景来描述进程管理和终端驱动相关的概念。

二、终端基础知识

本章分成两个部分，第一节描述了终端的概念，其他小节则介绍了形形色色的终端驱动。

1、什么是TTY，什么是终端？

TTY是TeleTYpe的缩写，直译成中文就是电传打字机。我们都熟悉telephone，phone本身是听筒或者那些发声或使用声音的工具，tele的含义则是指距离较远，需要通过电信号传递。同样的概念可以应用到teletype：type是指打字或者是印字的机构，tele则说明打字和印字机构相距比较远，需要通过电线传递信号。要理解Teletype这个概念需要回去过去的通信时代，最初发明的是电报，把message编成摩斯码，通过操作员将长长短短的tone音发送出去，在接收端，也会设立一个操作员，收听长长短短的tone音，还原message。这种通讯方式对人的要求很高，需要专门训练才能上岗，这严重阻碍了广大人民群众对交换信息的需求，因此teletype这样的机器被发明出来，它包括键盘模组、收发信息模组和字符打印模组（有些模组是机械的，因此，用现代语言，teletype也是一种机械电子设备）。发message时，需要不断的按下字符键，这些字符会被自动发送到电线上。收message的时候，接收器能自动接收来对端的字符信号，并打印出相应的字符。

计算机系统发明是比较靠后的事情了，肯定是比teletype晚。计算机系统需要输入和输出设备，而teletype包括了键盘和printer，可以作为计算机系统的输入和输出设备，因此，早期的计算机使用teletype作为终端设备（有些teletype设备也支持穿孔纸带作为输入或者用穿孔的纸带作为输出）。随着计算机工业的发展，teletype设备中的印字机构或者穿孔机构模块被显示器取代。其实，当teletype被应用到计算机系统中的时候，tty（teletype）这个术语已经不适用了（这时候tty没有传统的通信功能了，更多的是一个计算机系统的输入输出设备，也就是computer terminal），所以现在把tty称为终端会比较合适。

时代总是向前的，不论你愿不愿意。实际上目前的年轻的工程师都不太可能真正使用到终端设备，因为它被淘汰了。我在大学期间的计算机课程都是使用一台DEC VAX的大型机（mainframe computer），当然，我不是独占，这台大型机接出了30多台终端，每个同学拥有一个终端。而终端设备会从每个同学那里接收键盘输入，并且将这些输入通过串行通信的手段发送给VAX大型机，VAX大型机会处理每个用户的键盘输入和命令，然后输出返回并显示在每个终端的屏幕上。终端基本上都是text terminal，因此，主机和终端之间的串行通信都是基于字符的，终端收到字符后会显示在屏幕上。当进入微机（microcomputer）时代，每台主机都有自己的显示设备和键盘设备（多谢大规模集成电路的发展），图形显示器显示的都是点阵信息而不是基于字符的显示，LCD和键盘也不是通过慢速的串行通信设备和主CPU系统相连，从这个角度看，目前我们接触到的终端都不是真正的终端设备了，应该称之”终端仿真设备“。例如：我们可以通过windows系统中的一个窗口加上键盘设备组成一个终端，登录到本机或者远程主机。

2、什么是虚拟终端（Virtual Terminal）

虽然传统的终端设备随着时代的进步而消失了，但是我们仍然可以通过个人PC上的图形显示系统（SDRAM中的frame buffer加上LCD controller再加上display panel）和键盘来模拟传统的字符终端设备（所以称为虚拟终端设备）。整个系统的概念如下图所示：

![](/content/uploadfile/201610/74bd1477877203.gif)

由于已经不存在物理的终端设备了，因此Vitual Terminal不可能直接和硬件打交道，它要操作Display和Keyboard的硬件必须要通过Framebuffer的驱动和Keyboard driver。

虚拟终端不是实际的物理终端设备，之所以称为Virtual是因为可以在一个物理图形终端（键盘加上显示器）上同时运行若干个虚拟终端。虚拟终端也称为虚拟控制台（Virtual console）。对于linux系统而言，内核支持64个虚拟终端。用户可以通过Alt+Fx进行切换虚拟控制台。目前，GNU/linux操作系统在启动的时候支持6个虚拟终端，用户用Alt+F1 ～ F6进行切换，Alt+F7将切换到图形界面环境。一旦进入了图形桌面环境，可以通过Ctrl+Alt+Fx切回到字符界面的虚拟终端。关于图形界面下的终端相关的软件架构图我们会在后面的章节描述。

虚拟终端的主设备号是4，字符设备，前64个设备是虚拟控制台设备，具体的次设备号分配如下：

> 4 char TTY devices
>
> 0 = /dev/tty0 Current virtual console   
> 1 = /dev/tty1 First virtual console   
> ...   
> 63 = /dev/tty63 63rd virtual console

虽然内核支持了64个Virtual terminal设备，但是具体整个系统是否支持还是要看配置。一般而言，GNU/linux操作系统在启动的时候支持6个虚拟终端（使用tty1～tty6）。次设备号等于0的tty设备比较特殊，代表当前的虚拟控制台。如果不启动GUI系统，那么缺省tty0指向tty1，之后可以根据用户的动作进行切换，但是无论如何，tty0指向了当前的Virtual terminal。

3、什么是控制台（Console）

对于linux系统而言，控制台（console）或者系统控制台（system console）也是一种终端设备，但是又有其特殊性，如下：

（1）可以支持single user mode进行登录

（2）接收来自内核的日志信息和告警信息

在linux系统中，我们一般将系统控制台设备设定为其中一个虚拟终端（一般是当前的virtual terminal，也就是/dev/tty0），这样，我们可以在某一个virtual terminal上看到系统的message。在嵌入式的环境中，我们一般会将系统控制台设备设定为串口终端或者usb串口终端。

可以通过kernel启动的command line来设定系统控制台，例如：

> root=/dev/mtdblock0 console=ttyS2,115200 mem=64M

通过这样的设置可以选择串口设备做为系统控制台。

4、什么是伪终端（pseudo terminal或者PTY）

在linux中，伪终端是在无法通过常规终端设备（显示器和keyboard）登录系统的情况下（例如本主机的显示器和keyboard被GUI程序控制，疑惑本主机根本没有显示器和keyboard设备，只能通过网络登录），提供一种模拟终端操作的机制，它包括master和slave两部分。Slave device的行为类似物理终端设备，master设备被进程用来从slave device读出数据或者向slave device写入数据。通过这样的方法模拟了一个终端。那么为什么要有这样的伪终端设备，又为什么要有主设备和从设备配对呢?下面的图片可以给出解释：

![](/content/uploadfile/201610/189a1477877205.gif)

当然，大部分的用户在使用GNU/Linux系统的时候都是使用图形用户界面(GUI)系统，在这样的系统里，整个显示屏和键盘（也就是传统的虚拟终端设备）都在一个视窗管理进程的控制之下。从使用层面看，用户一般都是启动一个终端窗口程序来模拟命令行终端的场景。用户可以启动多个这样的窗口，每个这样的窗口都是一个进程，接收用户输入，期望和shell通过终端设备进行沟通。但是这时候，所有的窗口进程其实是无法打开并使用display＋key board终端设备的（GUI管理进程控制了实际的物理终端资源），怎么办呢？这就要使用伪终端设备了。 每一对伪终端设备连接着显示器上的一个终端窗口进程和一个shell进程。当视窗管理进程从键盘接收到一个字符时，该字符会被送到获得当前焦点的那个终端窗口进程，而终端窗口进程会将改字符送往与之对应的伪终端"主设备"。因此，对于键盘输入，视窗管理进程起着中转、分发的作用。而写入伪终端"主设备"一端的字符马上就到达了其"从设备"一端，在那里，对于与"从设备"关联的shell进程来说，其动作就跟从普通终端设备读入字符一模一样了。另外一个方向的通信也是类似的，这里就不再赘述了。

当然，和shell进程通过伪终端对进行连接的不一定非得是终端窗口进程，也可能是其他的进程，例如网络服务进程，这时候就是网络终端登录的场景了，其结构图也类似，大家可以自行补脑。

5、串口终端

串口终端好象没有什么好说的，大家都熟悉的很，这里就顺便说一下串口终端的设备节点吧，如下：

> 主设备号是4的字符设备是TTY devices，虚拟终端占据了0～63的minor设备号，之后的minor是串口设备使用   
> 64 = /dev/ttyS0 First UART serial port   
> ...   
> 255 = /dev/ttyS191 192nd UART serial port
>
> USB串口终端的主设备号是188的字符设备，这是主机侧的USB serial converters devices，具体如下：   
> 0 = /dev/ttyUSB0 First USB serial converter   
> 1 = /dev/ttyUSB1 Second USB serial converter   
> ...   
> 主设备号是127的字符设备是gadget侧的USB serial devices，具体如下：   
> 0 = /dev/ttyGS0 First USB serial converter   
> 1 = /dev/ttyGS1 Second USB serial converter   
> ...

三、进程管理中和终端相关的概念

1、什么是shell，什么是登录系统？

如果OS kernel是乌龟的身体，，那么shell就是保护乌龟身体的外壳。shell提供访问OS kernel服务的用户接口，用户通过shell可以控制整个系统的运行（例如文件移动、启动进程，停止进程等）。目前的shell主要有两种，一种就是大家熟悉的桌面环境，另外一种就是基于文本command line类型的，主要for业内人事使用。command line类型的shell虽然需要用户记住很多复杂的命令和脚本格式等等，但是其效率非常高，速度非常快。GUI类型的shell操作简单，用户容易上手，但效率为人所诟病。

上面说过了，shell是人类访问、控制计算机服务的接口，不过这个接口有些特殊，shell自己有自己的要求：用户不能通过任意的设备和shell交互，必须是一个终端设备。我们现在网络设备比较发达，可以通过网络设备直接和shell通信吗？不行，网络设备不是终端设备，想要通过网络设备访问shell，必须通过伪终端（后面会讲）。shell和人类交互的示意图如下：

![](/content/uploadfile/201610/e3921477877205.gif)

对于系统工程师，我们更关注command line类型的shell。在系统的启动过程中，init进程会根据/etc/inittab中的设定进行系统初始化（这里还是说的传统的系统启动过程，如果使用systemd那么启动过程将会不一样，但是概念类似），和tty相关的内容包括：

> 1:2345:respawn:/sbin/getty 38400 tty1   
> 2:23:respawn:/sbin/getty 38400 tty2   
> 3:23:respawn:/sbin/getty 38400 tty3   
> 4:23:respawn:/sbin/getty 38400 tty4   
> 5:23:respawn:/sbin/getty 38400 tty5   
> 6:23:respawn:/sbin/getty 38400 tty6

init进程会创建6个getty进程，这六个getty进程会分别监听在tty1～tty6这六个虚拟终端上，等待用户登录。用户登录之后会根据用户的配置文件（/etc/passwd）启动指定shell程序（例如/bin/bash）。因此，shell其实就是一个命令解析器，运行在拥有计算资源的一侧，通过tty驱动和对端tty设备（可能是物理的终端设备，也可能是模拟的）进行交互。

2、什么是Job control

和终端一样，Job control在现代操作系统中的需求已经不是那么明显，以至于很多工程师都不知道它的存在，不理解Job control相关的概念。在过去，计算机还是比较稀有的年代，每个工程师不可能拥有自己的计算机，工程师都是通过字符终端来登录计算机系统（当然，那个年代没有GUI系统），来分享共同的计算资源。在自己的终端界面上，任务一个个的串行执行，有没有可能让多个任务一起执行呢？（例如后台运行科学运算相关的程序，前台执行了小游戏放松一下）这就是job control的概念了。Job control功能其实就是在一个terminal上可以支持多个job（也就是进程组，后面会介绍）的控制（启动，结束，前后台转换等）。当然，在引入虚拟终端，特别是在GUI系统流行之后，Job control的需求已经弱化了，工程师在有多个任务需求的时候，可以多开一些虚拟终端，或者直接多开几个Termianl窗口程序就OK了，但是，Job control是POSIX标准规定的一个feature，因此，各种操作系统仍然愿意服从POSIX标准，这也使得job control这样的“历史功能”仍然存在现代的操作系统中。

如果不支持Job control，那么登录之后，可以通过终端设备和shell进行交互，执行Job A之后，用户可以通过终端和该进程组（也就是Job A）进行交互，当执行完毕之后，终端的控制权又返回给shell，然后通过用户在终端的输入，可以顺序执行Job B、Job C……在引入Job control概念之后，用户可以并行执行各种任务，也就是说Job A、Job B、Job C……都可以并行执行，当然前台任务（Job）只能有一个，所有其他的任务都是在后台运行，用户和该前台任何进行交互。

通过上面的描述，我们已经了解到了，在用户的操作下，多个Job可以并行执行，但是终端只有一个，而实际上每一个运行中的Job都是渴望和user进行交互，而要达成这个目标，其实核心要解决的问题就是终端的使用问题：

（1）终端的输入要递交给谁？

（2）各个进程是否能够向终端输出？

对于第一个问题，答案比较简单，用户在终端的输入当然是递交给前台Job了，但是那些后台任务需要终端输入的时候怎么办呢？这时候就需要任务控制（Job control）了，这里会涉及下面若干的动作：

（1）后台Job（后者说是后台进程组）对终端进行读访问的时候，终端驱动会发送一个SIGTTIN的信号给相应的后台进程组。

（2）该后台进程组的所有的进程收到SIGTTIN的信号会进入stop状态

（3）做为父进程的shell程序可以捕获该后台进程组的状态变化（wait或者waitpid），知道它已经进入stopped状态

（4）用户可以通过shell命令fg讲该后台进程组转入前台，从而使得它能够通过终端和用户进行交互。这时候，原来的前台任务则转入后台执行。

对于输入，我们严格限定了一个进程组做为接收者，但是对于输出的要求则没有那么严格，你可以有两种选择：

（1）前台任务和后台任务都可以向终端输出，当然，大家都输出，我估计这时候输出屏幕有些混乱，呵呵～～～

（2）前台任务可以输出，但是后台任务不可以。如果发生了后台任务对终端的写访问动作，终端驱动将发送SIGTOUT信号给相应的后台进程组。

除此之外，为了支持job control，终端驱动还需要支持信号相关的特殊字符，包括：

a) Suspend key（缺省control-Z），对应SIGTSTP信号

b) Quit key（缺省control-\），对应SIGQUIT信号

c) Interrupt key（缺省control-C），对应SIGINT信号，

当终端驱动收到用户输入的这些特殊字符的时候，会转换成相应的信号，发送给session中（后面会介绍该术语）的前台进程组，当然，前提是该终端是session的控制终端。因此，为了让那么多的进程组（Job）合理的、有序的使用终端，我们需要软件模块协同工作，具体包括：

（1）支持Job control的shell

（2）终端驱动需要支持Job control

（3）内核必须支持Job control的信号

3、什么是进程组？

简单的说，进程组就是一组进程的集合，当然，我们不会无缘无故的把他们组合起来，一定是有共同的特性，一方面，这些进程属于同一个Job，来自终端的信号可以送达这一进程组的每一个成员（是为了job control）。此外，我们可以通过killpg接口向一个进程组发送信号。任何一个进程都不是独立存在的，一定是属于某个进程组的，当fork的时候，该进程归入创建者进程所属的进程组，父进程在子进程exec之前可以设定子进程的进程组。比如说shell程序属于进程组A，当用户输入aaa程序fork一个新进程的时候（是shell创建了该进程，没有&符号，是前台进程），aaa进程则归属与进程组A（和shell程序属于同一个进程组），在exec aaa之前，会将其放入一个新的前台进程组，自己隐居幕后。如果用户输入aaa &，整个过程类似之前的描述，只不过shell保持在前台进程组。

通过上面的描述，很多工程师可能认为Shell可以同时运行一个前台进程和任意多个后台进程，其实不然，shell其实是以进程组（也就是Job了）来控制前台和后台的。我们给一个具体的例子：用户通过终端输入的一组命令行，命令之间通过管道连接，这些命令将会形成一个进程组，例如下面的命令：

> $ proc1 | proc2 &   
> $ proc3 | proc4 | proc5

对于第一行命令，shell创建了一个新的后台进程组，同时会创建两个进程proc1和proc2，并把这两个进程放入那个新创建的后台进程组（不能访问终端）。执行第二行命令的时候，shell创建了proc3、proc4和proc5三个进程，并把这三个进程加入shell新创建的前台进程组（可以访问终端）。

如何标识进程组呢？这里借用了进程ID来标识进程组。对于任何一个进程组，总有一个最开始的加入者，第一个加入者其实就是该进程组的创始者，我们称之为该进程组的Leader进程，也就是进程ID等于进程组ID的那个进程，或者说，我们用process leader的进程ID来做为process group的ID。当然，随着程序的执行，可能会有进程加入该进程组，也可能程序执行完毕，退出该进程组，对于进程组而言，即便是process group leader进程退出了，process group仍然可以存在，其生命周期直到进程组中最后一个进程终止, 或加入其他进程组为止。

通过getpgid接口函数，我们可以获取一个进程的进程组ID。通过setpgid接口函数，我们可以加入或者新建一个进程组。当然，进程组也不是任意创建或者加入的，一个进程只能控制自己或者它的子进程的进程组。而一旦子进程执行了exec函数之后，其父进程也无法通过setpgid控制该子进程的进程组。还需要注意的是：调用setpgid的进程、设定process group的进程和指定的process group必须在一个sesssion中。最后需要说的一点是：根据POSIX标准，我们不能修改session leader的进程组ID。

4、什么是Session？

从字面上看，session其实就是用户和计算机之间的一次对话，通俗的概念是这样的：你想使用计算机资源，当然不能随随便便的使用，需要召开一个会议，参加的会议双方分别是用户和计算机，用户把自己的想法需求告诉计算机，而计算机接收了用户的输入并把结果返回给用户。就这样用户和计算机之间一来一去，不断进行交互，直到会议结束。用户和计算机如何交互呢？用户是通过终端设备和计算机交互，而代表计算机和用户交互则是shell进程。每次当发生这种用户和计算机交互过程的时候，操作都会创建一个session，用来管理本次用户和计算机之间的交互。

如果支持job control，那么用户和计算机之间的session可能并行执行多个Job，而Job其实就是进程组的抽象，因此，session其实就是进程组的容器，其中容纳了一个前台进程组（只能有一个）和若干个后台进程组（当然，没有连接的控制终端的情况下，session也可能没有前台进程组，由若干后台进程组组成）。创建session的场景有两个：

（1）一次登录会形成一个session（我们称之login session，大部分的场景都是描述login session的）。

（2）系统的daemon进程会在各自的session中（我们称之daemon session）。

无论哪一个场景，都是通过setsid函数建立一个新的session（注意：调用该函数的进程不能是进程组的leader），由于创建了session，该进程也就成为这个新创建session的leader。之后，session leader创建的子进程，以及进程组也都属于该session。为何process group leader不能调用setsid来创建session呢？我们假设没有这个限制，process group leader（ID等于A）通过setsid把把自己加入另外一个新建的session，有了session就一定要有进程组，创建了sesssion的那个process group leader就成了该session中的第一个进程组leader，标识这个新建的进程组的ID就是A。而其他进程组中的成员仍然在旧的session中，在旧的session中仍然存在A进程组，这样一个进程组A的成员，部分属于新的session，部分属于旧的session，这是不符合session-process group2级拓扑结构的。我了满足这个要求，我们一般会先fork，然后让父进程退出，子进程执行setsid，fork之后，子进程不可能是进程组leader，因此满足上面的条件。

因此，setsid创建了新的session，同时也创建了新的process group，创建session的那个进程ID被用来标识该process group。新创建的sesssion没有控制终端，如果调用setsid的进程有控制终端，那么调用setsid之后，新的session和那个控制终端失去连接关系。如何标识session呢？我们往往使用session leader的process ID来标识。

5、控制终端（controlling terminal）

通过上面的描述，我们已经知道了：为了进行job control，我们把若干的进程组放入到了session这个容器进行管控。但是，用户如何来管控呢？必须要建立一个连接的管道，我们把和session关联的那个终端称为控制终端，把建立与控制终端连接的session首进程（session Leader）叫做控制进程（controlling process）。session可以有一个控制终端，不能有多个，当然也可以没有。而一个终端也只能和一个session对应，不能和多个session连接。

对于login session，我们登录的那个终端设备基本上就是该session的controlling terminal，而shell程序就是该session的leader，也是该session的controlling process。之所以会有controlling process的概念主要用来在终端设备断开的时候（例如网络登录的场景下，网线被拔出），终端驱动会把hangup signal送到对应session的controlling process。

session可以有一个前台进程组和若干个后台进程组（很好理解，占有控制终端的就是前台，没有的就是后台。当然可以一个前台进程组都没有，例如daemon session）。对于前台进程组，共同占有控制终端。在控制终端键入ctrl+c产生终止信号（或者其他可以产生信号的特殊字符组合）会被递交给前台进程组所有的进程（不会递交给后台进程）。虽然终端被前台进程组掌管，但是通过shell、内核和终端驱动的交互，后台进程组可以被推入到前台，也就是说：所有的session内的进程组可以分时复用该controlling terminal。

当创建一个session的时候，往往没有controlling terminal，当session leader open了一个终端设备，除非在open的时候指明O\_NOCTTY，否则该terminal就会称为该session的controlling terminal，当然，该终端也不能是其他session的controlling terminal，否则就会有一个控制终端对应两个session的状况发生了。一旦拥有了控制终端之后，session leader的子进程都会继承这个controlling terminal。除了上面说的隐含式的设定，程序也可以通过ioctl来显示的配置（TIOCSCTTY）controlling terminal，或者通过TIOCNOTTY来解除该终端和session的联系，变成一个普通的终端。

对于login session，session leader会建立和终端的连接，同时把标准输入、输出和错误定向到该终端。因此，对于后续使用shell运行的普通程序而言，我们不需要直接访问控制终端，一般是直接访问标准输入、输出和错误。如果的确是有需要（例如程序的标准输入、输出被重定向了），那么可以通过打开/dev/tty设备节点（major＝5，minor＝0）来访问控制终端，/dev/tty就是当前进程的控制终端。

四、应用

1、系统初始化

在系统启动的时候，swapper进程（或者称之idle进程）的信息整理如下：

|  |  |  |  |
| --- | --- | --- | --- |
| PID | PGID | SID | TTY |
| 0 | 0 | 0 | NO |

swapper进程在启动过程中会创建非常多的内核线程，这些内核线程的job control相关的信息如下：

|  |  |  |  |
| --- | --- | --- | --- |
| PID | PGID | SID | TTY |
| x | 0 | 0 | NO |

由此可见，所有内核线程都是在一个session中，属于一个进程组，随着内核线程的不断创建，其process ID从2开始，不断递增。Process ID等于1的那个进程保留给了init进程，这也是内核空间转去用户空间的接口，刚开始，init进程继承了swapper进程的sid和pgid，不过，init进程会在启动过程中调用setsid，从而创建新的session和process group，基本信息如下：

|  |  |  |  |
| --- | --- | --- | --- |
| PID | PGID | SID | TTY |
| 1 | 1 | 1 | NO |

2、虚拟终端登录

对于linux而言，/etc/inittab包括了登录信息，也就是说，init进程需要在哪些终端设备上执行fork动作，并执行（exec）getty程序，因此getty拥有自己的Process ID，并且是一个普通进程，不是session leader，也不是process group leader，在getty程序中会调用setsid，创建新的session和process group，同时，该程序会打开做为参数传递给它的终端设备（对应这个场景应该是ttyx），因此ttyx这个虚拟终端就成了该session的controlling terminal，gettty进程也就是controlling process。一旦正确的打开了终端设备，文件描述符0、1、2都定向到该终端设备。完成这些动作之后，通过标准输出向用户提示登录信息（例如login:）。在用户输入用户名之后，getty进程已经完成其历史使命，它会调用exec加载login程序（PID、PGID、SID都没有变化）。

login进程最重要的任务当然是鉴权了，如果鉴权失败，那么login进程退出执行，而其父进程（也就是init进程）会侦听该事件并重复执行getty。如果鉴权成功，那么login进程会fork子进程并执行shell。刚开始，login进程和shell进程属于一个session，同时也属于同一个前台进程组，共享同一个虚拟终端，也就是说两个进程的controlling terminal都是指向该登录使用的那个虚拟终端。shell进程并非池中之物，最终还是要和login进程分道扬镳的。shell进程会执行setpgid来创建一个新的进程组，然后调用tcsetpgrp将shell所在的进程组设定为前台进程组。

注：上面的描述是基于Debian 8系统描述的。

2、shell执行命令

在虚拟终端登陆后，我们可以执行下面的命令：

> #ps –eo stat,comm,sid,pid,pgid,tty | grep tty | more

shell执行这一条命令的动作示意图如下：

![](/content/uploadfile/201610/3ae41477877202.gif)

在/dev/tty1完成登录之后，系统存在两个进程组，前台进程组是shell，后台进程组是login，两个进程组都属于一个session，所有进程的控制终端都是虚拟终端tty1。执行上述命令之后，shell创建了3个进程ps、grep和more，并将这三个进程放到一个新创建的进程组中（ps是进程组leader），同时把该进程组推向前台，shell自己隐居幕后。一旦程序执行完毕，后台的shell收到子进程的信号后，又把自己推到前台来，等待用户输入的下一条命令。

我们假设用户输入下面的命令：

> #ps –eo stat,comm,sid,pid,pgid,tty | grep tty | more &

&符号其实就是后台执行的命令，shell执行这条命令的过程和上图类似，不过这时候并不把新建立的进程组推到前台，shell自己仍然是前台进程组。由于有pipe，输出信息沿着ps—>grep--->more的路径来到了more进程，more进程输出到标准输出，也就是tty1这个虚拟终端的时候，悲剧发生了，后台进程组不能write控制终端，从而引发了SIGTOUT被发送到该后台进程组的每一个进程组，因此，ps，grep和more都进入stop状态。这时候只要在shell执行fg的操作，就可以把ps那个后台进程组推到前台，这时候虚拟终端的屏幕才会打印出相关的进程信息。

3、GUI系统

TODO （对GUI系统不熟悉，只能暂时TODO了，哈哈）

五、参考文献

1、Unix高级环境编程

2、POSIX标准

3、The Linux Programming Interface - A Linux and UNIX System Programming Handbook

*原创文章，转发请注明出处。蜗窝科技*
