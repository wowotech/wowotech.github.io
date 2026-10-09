---
title: "Linux TTY framework(3)_从应用的角度看TTY设备"
date: 2016-10-14T22:13:33+08:00
url: "/tty_framework/application_view.html"
gid: "342"
emlog_type: "blog"
summary: "可以毫不夸张的说，我们在使用Linux系统的过程中，每时每刻都在和TTY打交道，显示输出、键盘输入、用户登录、shell终端、等等。 与此同时，作为软件工程师的我们，也会或多或少的困惑：这些习以为常的行为，怎么和kernel中的这些冷冰冰的代码联系起来的？ 因此，在Linux TTY framework分析工作正式开始之前，让我们带着上面的疑问，以这些熟悉的应用场景为视角，进一步理解TTY有关的概"
author: "wowo"
category: "TTY子系统"
category_alias: "tty_framework"
tags: ["Linux", "tty", "console", "vt", "虚拟终端", "pty", "伪终端", "控制终端"]
views: 25470
comment_count: 24
aliases:
  - "/tty_framework/342.html"
  - "/342.html"
---

## 1. 前言

可以毫不夸张的说，我们在使用Linux系统的过程中，每时每刻都在和TTY打交道，显示输出、键盘输入、用户登录、shell终端、等等。

与此同时，作为软件工程师的我们，也会或多或少的困惑：这些习以为常的行为，怎么和kernel中的这些冷冰冰的代码联系起来的？

因此，在Linux TTY framework分析工作正式开始之前，让我们带着上面的疑问，以这些熟悉的应用场景为视角，进一步理解TTY有关的概念。这就是本文的目的。

## 2. 再谈终端（Terminal）设备

我们在“[Linux TTY framework(1)\_基本概念](/tty_framework/tty_concept.html)”中简单的提过，终端设备是指那些帮助我们和计算机进行人机交互的设备，所谓的人机交互，可简单的总结为：

> 输入（input），向计算机发送指令；
>
> 输出（output），计算机将执行结果显示出来。

与此同时，关于输入/输出，可提出如下疑问（为了简单，将输入、输出看作一个统一的整体，即终端）：

> 输入、输出设备是什么？
>
> 计算机怎么接收和输出？
>
> 人怎么接收和输出（这个就不用回答了，大家都知道，呵呵）。

关于这两个疑问，下面我们分别讨论。

#### 2.1 终端的类型

根据不同的输入、输出设备类型，我们常见的终端有如下几类：

1）控制台终端（console）

> 这类终端的输入设备通常是键盘，输出设备通常是显示器；
>
> 输入、输出设备通过各类总线直接和计算机相连；
>
> “终端”其实是这些设备的一个逻辑抽象。

2）虚拟终端（VT）

> 控制台终端的输出设备（显示器）一般只有一个，同一时刻由一个应用程序独占；
>
> 但在多任务的操作环境中，有时需要在将终端切换给另一个应用程序之前，保留当前应用在终端上的输出，以方便后面查看；
>
> 因此Unix/Linux系统在控制台终端的基础上，又虚拟出来6个终端----称作虚拟终端，不同的应用程序可以在这些虚拟终端上独立的输出，在需要的时候，可以通过键盘的组合键（CTRL+ALT+ F1~F6）将某一个虚拟终端调出来在屏幕上显示。

3）串口终端（TTY）

这是正牌的TTY设备：

> 输入设备和输出设备集成在一个独立的硬件上（称作TTY设备），这个硬件和计算机通过串口连接；
>
> 输入设备（键盘）的输入动作，将会转换为串口上的RX数据包（以计算机为视角），发送给计算机；
>
> 计算机的输出会以TX数据包的形式发送给TTY设备，TTY设备转换后在输出设备（屏幕）上显示。

4）软件终端

这是我们现在最常用的终端：

> 既然人机交互的数据流可以封装后经过串口传输，那么终端设备的形式就不再受限了，只要可以接收用户的输入并打包通过串口发送给计算机，以及接收计算机从串口发来的输出并显示出来，任何设备都可以变成终端设备，例如另一台计算机；
>
> 当另一台计算机被当作终端设备时，通常不会把它的所有资源都用来和对端进行人机交互，常用的方法是，在这个计算机上利用软件，模拟出来一个“终端设备”。该软件就像一个中间商：从键盘接收用户输入，然后控制串口发送给对端；从串口接收对端的输出，然后在软件界面上显示出来；
>
> 平时大家经常使用的PuTTY、SecureCRT、Windows超级终端、等等，都是“软件终端”。

5）USB、网络等终端

> 既然串口可以作为人机交互数据的传说媒介，其它通信接口一样可以，例如USB、Ethernet、等等，其原理和串口终端完全一样，这里不再过多说明。

6）图形终端

> 前面所介绍的那些终端，人机交互的输出界面都是字符界面，随着计算机技术的发展，GUI界面慢慢出现并成为主流，这些通过GUI交互的形式，也可以称作图形终端。不过这已经超出了TTY framework系列文章的讨论范围了，因为TTY的势力范围只涵盖字符界面。

#### 2.2 输入和输出

首先声明，这里的输入和输出，都是针对计算机设备而言。

另外，计算机是一个硬件设备，它本身没有输入和输出的自主意识，因此，输入和输出，都是指运行在计算机中的软件，所谓的人机交互，其实是人和一个个的软件交互。

以Linux系统为例：

> kernel会通过控制台终端输出日志信息（printk）；
>
> kernel启动之后，init进程会打开控制台终端，以便和我们交互（接收一些指令并应答、输出日志信息、等等）；
>
> 随后，getty应用可以打开任意的终端设备，和我们交互，以便我们可以登入系统；
>
> 登入系统之后，getty将终端的控制权交给shell（bash、sh等等），我们与之交互，进行着愉快的人机对话，巴拉巴拉……
>
> 当然，在人机对话的过程中，我们可以命令shell启动其它的应用，例如地图应用，该应用可能会打开另一个TTY设备（例如GPS UART），并与之交互（由此可见，上面提到的人机交互其实是狭隘的概念，也可以机机交互~~）；
>
> 等等，等等。

## 3. 软件视角

讲完概念，我们还是要回到软件上来，厘清Linux TTY framework中的那些奇怪概念。

注1：建议读者结合“[Linux TTY framework框架](/content/uploadfile/201609/588316ff34005cfdf8f214ff4c806cda20160927144244.gif)[1]”阅读本节内容。

#### 3.1 console driver

Linux系统中可以存在多个种类各异的终端设备，工程师会使用一个个的TTY driver（struct tty\_driver）驱动它们。如果某些我们需要让某些终端作为控制台终端，可以基于TTY driver，创建对应的console driver，并注册给kernel。

关于console driver，kernel有如下的策略：

1）可以同时注册多个console driver，并有选择的使用。

2）可以在kernel启动的时候，通过命令行（或者后来的device tree），告诉kernel使用哪个或者哪些控制台终端。例如：

> console=”/dev/ttyS0”, console=”/dev/ttyUSB0”

3）对kernel的日志输出来说，可以在所有被选中的控制台终端上输出。

4）后续可用作人机交互的控制台终端只能有一个（后指定的那个）。

#### 3.2 控制台终端（/dev/console）

前面提到过，控制台终端只能有一个（最后指定的那个），那么“/dev/console”又是怎么回事呢？

了解linux kernel启动过程的同学都知道，kernel启动的后期，会在kernel\_init线程（最后会退化为init进程）中打开控制台终端。但是由上面3.1小节的介绍可知，控制台终端的类型、名称是五花八门的，怎么让kernel的核心代码无视这些差异呢？这就是“/dev/console”的存在意义：

由“[Linux TTY framework(2)\_软件架构](/tty_framework/tty_architecture.html)[2]”中的介绍可知，/dev/console的设备号固定为(5, 1) ，当init线程打开该设备的时候，TTY core会问system console core：喂，哪一个终端适合做控制台终端啊？

因此，最终打开的是那个具体的、可以当作控制台终端的设备，而“/dev/console”，仅仅是一个占位坑，如下图所示：

[![dev_console](/content/uploadfile/201610/258ee432c25b83718b282f68b481b6e720161014141331.gif "dev_console")](/content/uploadfile/201610/3418457a253b8bbfac7516359f59512c20161014141331.gif)

#### 3.3 虚拟终端（/dev/ttyN）

正如其名，虚拟终端是虚拟出来的一个终端，不对应具体的设备（屏幕和键盘）。应用程序可以打开某一个虚拟终端，以便和人进行交互。

对应用程序而言，这个终端和具体的物理终端，没有任何区别（应用程序也无法区分）。而对整个系统来说，由于物理资源（键盘和屏幕）只有一套，因此同一时刻只能和某一个虚拟终端对接。从另一个角度看，各个虚拟终端轮流使用物理资源和人进行交互，如下所示：

[![vt](/content/uploadfile/201610/c1e5e2b116e8b9f3e7e37ca195929d6420161014141332.gif "vt")](/content/uploadfile/201610/705cae2cebc49ecec7aef407a9e075b920161014141331.gif)

#### 3.4 伪终端(Pseudo Terminal，pty)

前面提到过，既然串口（serial）可用作终端和计算机之间的数据传输通道，那么其它诸如Ethernet的通信介质，也可以实现类似的功能。但这里面有一个问题（以网络为例）：

> Linux系统中的网络驱动，并不是以TTY的形式提供API（众所周知，网络使用socket接口）。因此，系统中的应用程序，无法直接打开网络设备，进而和对应的终端设备通信。怎么办？

解决方案就是伪终端（英文为Pseudo Terminal，简称pty）。字面上理解，伪终端根本不是终端（虚拟终端好歹还是），是为了让应用程序可以从网络等非串口类的接口上，和终端设备交互而伪造出来的一种东西。它的原理如下：

> pty由pts(pseudo-terminal slave)和ptm(pseudo-terminal master)两部分组成。
>
> pts伪造出一个标准的TTY设备，应用程序可以直接访问。应用程序向pts写入的数据，会直接反映到ptm上，同样，应用程序从pts读数据，则相当于直接从ptm读取。
>
> 而pym，则根据具体情况，具体实现。例如：要通过网络接口和终端设备交互，则pym需要打开对应的socket，将pts写来的数据，从socket送出，将从socket读取的数据，送回给pts。

有了伪终端，Unix/Linux系统中的终端设备就可以脱离具体的物理限制，可以是任何形态，例如在GUI环境中，使用Terminal软件（如xterm）模拟出来的终端，其原理为：

> 用户启动xterm等Terminal软件的时候，该软件会生成一对pts和ptm，同时执行shell应用；
>
> Terminal软件会将pts交给shell应用，shell应用傻傻分不清，还以为它是一个标准的TTY设备呢，欢快的运行了；
>
> shell从pts读入数据，相当于从ptm读入；shell向pts输出数据，相当于向ptm写入；这是由TTY framework自动完成的，不需要Terminal软件关心；
>
> 在另一端，Terminal软件将会从ptm读取数据（实际上是shell通过pts写入的数据），并显示在自己的GUI窗口上；于此同时，Terminal软件会从自己的GUI窗口接收用户输入，并通过pts转给shell，太完美了。

上面提到了有关伪终端的两个例子，其示意图图下：

[![pty](/content/uploadfile/201610/fba3b79637da181277c1041ed86fdd4f20161017140017.gif "pty")](/content/uploadfile/201610/e9ce512d7ffd595accc2c8b669583edd20161017140013.gif)

#### 3.5 控制终端（control terminal，/dev/tty）

讲到控制终端（control terminal），就不得不提Unix/Linux的Job control[3]功能。有关job control，感兴趣的读者可以参考其它文章（如[3]），这里简单总结如下：

> 1）job control是Unix/Linux shell（记住，shell是一个应用程序）中的概念，是shell用来管理、控制jobs的一种方法。
>
> 2）job是进程组（process group[4]）在shell中的体现。换句话说，shell借用进程组实现了job。
>
> 3）进程组（或者job，在本文中可以等同，后面不在区分）是多个进程的组合。

基于上面简单的知识（不一定准确，但不影响我们对控制终端的理解），我们引入控制终端的概念：

> 1）通常情况下，Linux启动后，终端（以后都用TTY指代）的控制权会交给shell（一种应用程序）。所谓的控制权，就是指shell程序可以通过TTY读取终端的输入，以及通过TTY向终端输出。
>
> 2）通过shell，可以启动其它的应用程序，相应地，应用程序在需要的时候也会获得TTY的控制权。
>
> 3）同一时刻，只能有一个应用可以占有TTY，即只有一个应用可以通过TTY输入、输出。
>
> 4）那个占有TTY、可以进行输入输出的应用，称作前台应用。相应的，不能进行输入输出的应用，称作后台应用。因此，shell中只有一个前台应用，可以有多个后台应用。
>
> 5）然后，问题就来了：如果某个后台应用，就是想输入输出，怎么办？有一个办法，就是通过控制终端（control terminal）。
>
> 6）控制终端在Linux中的名称固定为/dev/tty, 设备号为(5, 0)，作用和/dev/console类似，进程可以通过TTY core提供的ioctl，选择控制终端所对应的实际的终端设备。
>
> 7）暂且抛开前台应用不谈（因为人家有TTY设备），对于那些后台应用，如果想输入输出，可以读取或者写入控制终端。此时，一般情况下，TTY core会向后台应用发送SIGTTIN(读取控制终端时) 或者 SIGTTOU（写入控制终端时）信号，这会终止该后台应用。
>
> 8）不过，shell会重设收到 SIGTTOU信号时的行为，于是，后台应用写入的内容，可以通过控制终端显示出来。

## 4. 参考文档

[1] [Linux TTY framework框架](/content/uploadfile/201609/588316ff34005cfdf8f214ff4c806cda20160927144244.gif)

[2] [Linux TTY framework(2)\_软件架构](/tty_framework/tty_architecture.html)

[3] <https://en.wikipedia.org/wiki/Job_control_(Unix)>

[4] [/process_management/process_identification.html](/process_management/process_identification.html "/process_management/process_identification.html")

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/tty_framework/application_view.html)。
