---
title: "systemd：为何要创建一个新的init系统软件"
date: 2016-03-17T18:27:07+08:00
url: "/linux_application/why-systemd.html"
gid: "272"
emlog_type: "blog"
summary: "\r\n\t当我把我的电脑升级到Debian 8的时候，赫然发现旧的SysV \r\ninit的东西似乎是消失了，取而代之的是systemd。当然，它不是个新东西，只不过一方面多年来我只是关注内核，很少理会用户空间的东西，此外，公\r\n司的操作系统始终封存在linux2.6.23上，各种rootfs的software \r\npackage也从未升级，因此我已经和世界脱轨了。不过没有关系，活到老学到老，本文主要解"
author: "linuxer"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["systemd"]
views: 22908
comment_count: 2
aliases:
  - "/linux_application/272.html"
  - "/272.html"
---

当我把我的电脑升级到Debian 8的时候，赫然发现旧的SysV init的东西似乎是消失了，取而代之的是systemd。当然，它不是个新东西，只不过一方面多年来我只是关注内核，很少理会用户空间的东西，此外，公司的操作系统始终封存在linux2.6.23上，各种rootfs的software package也从未升级，因此我已经和世界脱轨了。不过没有关系，活到老学到老，本文主要解决一个问题：多年来SysV init系统软件已经象呼吸一样自然了，为何会有systemd这个新的init system呢？

本来想自己整理一下资料，写一篇相关文档，最终发现systemd项目的发起者的一篇博客其实完美的回答了这个问题，因此本文实际上也就是针对[http://0pointer.de/blog/projects/systemd.html](http://0pointer.de/blog/projects/systemd.html "http://0pointer.de/blog/projects/systemd.html") 文档的翻译，这篇博文中详细的描述了systemd的故事。

If you are well connected or good at reading between the lines you might already know what this blog post is about. But even then you may find this story interesting. So grab a cup of coffee, sit down, and read what's coming.

This blog story is long, so even though I can only recommend reading the long story, here's the one sentence summary: we are experimenting with a new init system and it is fun.

[Here's the code.](http://git.0pointer.de/?p=systemd.git) And here's the story:

如果你经常在网上了解一些新技术或者善于在字里行间发现一些新的设计思考，那么你应该早就知道这片博文讲的是什么了。不过，也许在那个时候，你就已经发现了这个故事很有趣的事实。因此，手握一杯咖啡，坐下来，看看什么新技术会即将到来。

这篇博文的故事很长，虽然我推荐您阅读整个故事的来龙去脉，不过，也可以一句话简单的说：我们正在尝试一个新的init系统，并且很有趣。

代码在这里：[https://github.com/systemd/systemd](https://github.com/systemd/systemd "https://github.com/systemd/systemd")。下面是关于这个新init系统软件的故事。

**Process Identifier 1**

On every Unix system there is one process with the special process identifier 1. It is started by the kernel before all other processes and is the parent process for all those other processes that have nobody else to be child of. Due to that it can do a lot of stuff that other processes cannot do. And it is also responsible for some things that other processes are not responsible for, such as bringing up and maintaining userspace during boot.

Historically on Linux the software acting as PID 1 was the venerable sysvinit package, though it had been showing its age for quite a while. Many replacements have been suggested, only one of them really took off: [Upstart](http://upstart.ubuntu.com/), which has by now found its way into all major distributions.

As mentioned, the central responsibility of an init system is to bring up userspace. And a good init system does that fast. Unfortunately, the traditional SysV init system was not particularly fast.

For a fast and efficient boot-up two things are crucial:

- To start **less**.
- And to start **more** in *parallel*.

What does that mean? Starting less means starting fewer services or deferring the starting of services until they are actually needed. There are some services where we know that they will be required sooner or later (syslog, D-Bus system bus, etc.), but for many others this isn't the case. For example, bluetoothd does not need to be running unless a bluetooth dongle is actually plugged in or an application wants to talk to its D-Bus interfaces. Same for a printing system: unless the machine physically is connected to a printer, or an application wants to print something, there is no need to run a printing daemon such as CUPS. Avahi: if the machine is not connected to a network, there is no need to run [Avahi](http://avahi.org), unless some application wants to use its APIs. And even SSH: as long as nobody wants to contact your machine there is no need to run it, as long as it is then started on the first connection. (And admit it, on most machines where sshd might be listening somebody connects to it only every other month or so.)

Starting more in parallel means that if we have to run something, we should not serialize its start-up (as sysvinit does), but run it all at the same time, so that the available CPU and disk IO bandwidth is maxed out, and hence the overall start-up time minimized.

**PID等于1的那个进程是什么呢？**

在每一个Unix的系统上都有一个PID等于1的特殊进程，它是由内核启动的第一个用户空间进程，是在所有其他用户空间进程启动之前就存在了，如果系统中的用户进程找不到其父进程（例如父进程退出），那么这个PID等义1的进程会收养该进程，成为该进程的父进程。正因为如此，这个PID等于1的进程很特殊，能够做一些其他普通进程不能完成的杂七杂八的事情，也承担了一些其它进程无法负担的任务，例如在系统启动过程中负责将用户空间的进程一个个的启动起来并且对其进行维护。

纵观Linux的历史，完成PID等于1这个进程功能的软件包是神圣而庄严的SysVinit，从开始到现在已经持续了有一段时间了。很多人对它不满意并提出了一些建议性的项目来替代sysVinit，不过只有一个真正的启动并获取了成功，它就是[Upstart](http://upstart.ubuntu.com/)，现在，在很多的主流发行版上都可以看到它的身影。

就像之前说的那样，init系统软件的核心功能就是启动用户空间的进程，一个好的init系统软件在做这件事情的时候应该非常快，但是不幸的是：传统的sysV的init系统软件并不是那么的快。要想快速有效的启动，两件事情很关键：

（1）进程启动的数目少一点

（2）尽量并行化启动进程

具体什么意思呢？启动进程少一点也就是意味着系统中的各种服务不要一开始就启动起来，而是delay到用户确实是需要它的时候再启动。当然，我们知道有些服务（例如syslog，D-Bus的system bus服务进程等）或早或晚都会被使用到，因此在启动过程中加载该服务是适合的，不过大部分的服务并非如此。例如，对于蓝牙服务（bluetoothd），在蓝牙dongle没有插入计算机或者用户没有要求启动蓝牙服务（通过D-Bus的接口）的时候，其实该服务是需要启动的。同样的，打印服务也是这样，除非计算机连接了打印机或者某个应用想要打印点什么东西，否则我们没有必要在启动阶段激活打印服务进程（CUPS）。我们再来看看Avahi，如果计算机没有连接网络，其实没有必要启动该服务，除非其他应用想要使用它的接口API。还有SSH服务，如果没有用户想要通过SSH客户端登录系统，那么该服务也没有必要启动，直到第一个连接被建立（不过事实是这样的：在大部分的计算机系统中，也许sshd服务只是一个月偶尔使用一次，但是该服务也是从系统启动开始，顽强的监听在某个端口上等待请求的来临）。

让更多的进程并行化启动是什么意思呢？就是说，如果我们必须要启动一些进程，那么我们尽量不要一个一个串行化启动进程（sysVinit就是这么做的），而是同时启动它们，这样CPU和DISK IO可以发挥它们最大的带宽，从而减少启动时间。

**Hardware and Software Change Dynamically**

Modern systems (especially general purpose OS) are highly dynamic in their configuration and use: they are mobile, different applications are started and stopped, different hardware added and removed again. An init system that is responsible for maintaining services needs to listen to hardware and software changes. It needs to dynamically start (and sometimes stop) services as they are needed to run a program or enable some hardware.

Most current systems that try to parallelize boot-up still synchronize the start-up of the various daemons involved: since Avahi needs D-Bus, D-Bus is started first, and only when D-Bus signals that it is ready, Avahi is started too. Similar for other services: livirtd and X11 need HAL (well, I am considering the Fedora 13 services here, ignore that HAL is obsolete), hence HAL is started first, before livirtd and X11 are started. And libvirtd also needs Avahi, so it waits for Avahi too. And all of them require syslog, so they all wait until Syslog is fully started up and initialized. And so on.

**动态变化的软件和硬件**

现代操作系统（特别是通用操作系统）要面对不断动态变化的配置和应用场景：软件和硬件模块都是变化的，不同的应用程序被启动，被停止，不同的硬件去去又来。负责维护各种service状态的init系统软件必要要监听各种硬件和软件的变化，并且根据这些变化启动（或者停止）某些service，而这些service又会执行某些程序或者enable某些硬件。

对于那些想要并行化启动的操作系统，它们的init系统软件需要对启动过程所设计的各种daemon进行进行同步：由于Avahi需要D-Bus，因此D-Bus daemon需要首先启动，只有在收到D-Bus的ready信号之后，Avahi进程再被启动起来。其他的各种服务进程也类似：livirtd和X11需要HAL（好吧，其实HAL服务已经过时了，现在被udev取代了，不过这里只是举例，就当我们回到了古老的Fedora 13好了），因此HAL服务进程先于livirtd和X11启动，通话四livirtd也需要Avahi服务，因此它也会等待Avahi服务。这些所有的服务进程都需要syslog，这些进程都要等待syslog服务完全ready之后才开始进行初始化过程，其他的过程也大概类似如此。

**Parallelizing Socket Services**

This kind of start-up synchronization results in the serialization of a significant part of the boot process. Wouldn't it be great if we could get rid of the synchronization and serialization cost? Well, we can, actually. For that, we need to understand what exactly the daemons require from each other, and why their start-up is delayed. For traditional Unix daemons, there's one answer to it: they wait until the socket the other daemon offers its services on is ready for connections. Usually that is an AF\_UNIX socket in the file-system, but it could be AF\_INET[6], too. For example, clients of D-Bus wait that /var/run/dbus/system\_bus\_socket can be connected to, clients of syslog wait for /dev/log, clients of CUPS wait for /var/run/cups/cups.sock and NFS mounts wait for /var/run/rpcbind.sock and the portmapper IP port, and so on. And think about it, this is actually the only thing they wait for!

Now, if that's all they are waiting for, if we manage to make those sockets available for connection earlier and only actually wait for that instead of the full daemon start-up, then we can speed up the entire boot and start more processes in parallel. So, how can we do that? Actually quite easily in Unix-like systems: we can create the listening sockets **before** we actually start the daemon, and then just pass the socket during exec() to it. That way, we can create **all** sockets for **all** daemons in one step in the init system, and then in a second step run all daemons at once. If a service needs another, and it is not fully started up, that's completely OK: what will happen is that the connection is queued in the providing service and the client will potentially block on that single request. But only that one client will block and only on that one request. Also, dependencies between services will no longer necessarily have to be configured to allow proper parallelized start-up: if we start all sockets at once and a service needs another it can be sure that it can connect to its socket.

**如何让有socket依赖关系的服务进程并行化执行呢？**

这种类型的启动同步（指socket依赖）是导致启动过程串行化执行的最大的元凶，有没有什么好的办法来解除这种类型的同步以及串行化带来的时间开销的呢？呵呵，有，当然有了。为了达到这个目的我们需要仔细理解需要同步的daemon之间是如何耦合的，为何一个daemon要等待另外一个启动完成才开始执行。对于传统的Unix daemon而言，其实不难回答这个问题：因为delay执行的那个daemon必须要原地待命，直到需要提供服务的daemon能够创建好socket并准备好处理各种连接请求。一般而言，这种socket都是文件系统中的domain socket，当然也有可能是实际的AF\_INET socket。我们来举一个实际的例子：D-Bus的客户端需要/var/run/dbus/system\_bus\_socket 这个domain socket准备好，以便可以连接上和D-Bus system daemon进行通信。syslog的客户端需要等待/dev/log，CPUS的客户端需要等待/var/run/cups/cups.sock，NFS mounts需要等待/var/run/rpcbind.sock和portmapper IP port，socket的依赖大概都是类似如此。仔细想一想，socket依赖其实就是一个进程等待另外一个进程的socket ready for connection而已。

好，现在我们看到了socket依赖的本质，知道了进程在等待什么了，但是把等待一个socket变成等待一个daemon启动完成真的合理吗？如果我们一早就准备好这个ready for connection的socket，那么socket依赖的daemons不就可以愉快的一起玩耍（并行启动）了吗？这样，我们也就加快了启动过程，让更多的进程可以并发执行了。具体怎么做呢？easy，就像某品牌的点读机一样so easy，对于unix-like的系统，我们可以在启动daemon进程之前，由init进程创建那个等待连接的socket，当init进程调用exec启动daemon进程的时候，将这个创建好的socket被传递到了具体的要启动的daemon进程中来。通过这个方法，我们两步搞定socket依赖。第一步让init系统软件创建所有的等待连接的socket，第二步并行化启动所有的daemon进程。如果一个服务进程需要另外一个服务进程提供的服务，那么该服务进程应该不能完全的完成其启动过程，这也没有什么问题，对于提供服务的进程而言，连接请求会放入队列。对于请求服务的daemon而言，也就是阻塞在这个连接请求上而已。想一想，只有一个客户端程序阻塞在一个请求上，这个结果也是可以接受的。此外，服务进程之间的依赖不复存在，你也不必去配置正确的并行启动顺序，要知道，我们是在init系统软件中一次性的创建所有的socket，即便是client先于提供服务的daemon启动并且连接到socket，其实也没有问题，只不过，在那一刻，对端是init进程而已。

Because this is at the core of what is following, let me say this again, with different words and by example: if you start syslog and and various syslog clients at the same time, what will happen in the scheme pointed out above is that the messages of the clients will be added to the /dev/log socket buffer. As long as that buffer doesn't run full, the clients will not have to wait in any way and can immediately proceed with their start-up. As soon as syslog itself finished start-up, it will dequeue all messages and process them. Another example: we start D-Bus and several clients at the same time. If a synchronous bus request is sent and hence a reply expected, what will happen is that the client will have to block, however only that one client and only until D-Bus managed to catch up and process it.

Basically, the kernel socket buffers help us to maximize parallelization, and the ordering and synchronization is done by the kernel, without any further management from userspace! And if all the sockets are available before the daemons actually start-up, dependency management also becomes redundant (or at least secondary): if a daemon needs another daemon, it will just connect to it. If the other daemon is already started, this will immediately succeed. If it isn't started but in the process of being started, the first daemon will not even have to wait for it, unless it issues a synchronous request. And even if the other daemon is not running at all, it can be auto-spawned. From the first daemon's perspective there is no difference, hence dependency management becomes mostly unnecessary or at least secondary, and all of this in optimal parallelization and optionally with on-demand loading. On top of this, this is also more robust, because the sockets stay available regardless whether the actual daemons might temporarily become unavailable (maybe due to crashing). In fact, you can easily write a daemon with this that can run, and exit (or crash), and run again and exit again (and so on), and all of that without the clients noticing or loosing any request.

由于解socket依赖是理解下文的关键所在，因此，让我们换一种表述方法再说一遍，同时提供示例。如果我们同时启动syslog daemon和需要该服务的client进程，会发生什么呢？就像上文所说的那样，client发出的message会加入到/dev/log的socket buffer中。只要这个socket buffer还没有满，这个client就可以继续执行启动过程而不需要等待。一旦syslog daemon完成启动，它就会从socket buffer中读取数据并处理它。另外一个例子是来自D-Bus和它的client同时启动的例子：如果一个同步的dbus总线请求被发送的bus上并且期待一个回复，在这种情况下，client只能被阻塞，当然只是阻塞那一个client进程而已。只有在D-Bus system daemon进程启动之后并且处理该请求之后，client进程才能解除阻塞状态。

本质上说，kernel的socket buffer帮助我们并行最大化，顺序和同步的问题都是在内核中完成，不需要用户空间更多的参与。如果所有的socket在各种系统daemon启动之前就准备好，那么依赖性管理也变得多余（或者说至少没有那么重要了）：如果A daemon需要B daemon的服务，那么直接连上就OK了，不需要考虑B daemon是否已经完成启动。如果B daemon已经完成启动，那么A和B之间的socket通信管道已经OK了。如果B正在启动的过程中，那么A进程也不要等待它，除非A进程发送一个同步请求（需要回应）给B进程。如果B进程根本没有启动，那么A的连接事件也可以做为一个触发机制，让B自动开始其启动过程。不管什么场景，从A进程的角度来看没有什么区分，因此，我们说依赖性管理是多余的（或者说次要的），一切都是优化的并行化处理，如果你愿意，还可以选择实现按需加载daemon。从更高层次来看，这样会让系统具有更好的鲁棒性：因为socket总是ready的，不管实际的daemon如何乱搞，例如启动、退出，再次启动，crash之后，再重新来过等等，这些都不会给client带来任何的困扰，client发送的message也会安静的呆在socket buffer中，等待那个实际要处理的daemon历经百转千回的启动过程来真正处理。

It's a good time for a pause, go and refill your coffee mug, and be assured, there is more interesting stuff following.

But first, let's clear a few things up: is this kind of logic new? No, it certainly is not. The most prominent system that works like this is Apple's launchd system: on MacOS the listening of the sockets is pulled out of all daemons and done by launchd. The services themselves hence can all start up in parallel and dependencies need not to be configured for them. And that is actually a really ingenious design, and the primary reason why MacOS manages to provide the fantastic boot-up times it provides. I can highly recommend [this video](https://www.youtube.com/watch?v=SjrtySM9Dns) where the launchd folks explain what they are doing. Unfortunately this idea never really took on outside of the Apple camp.

The idea is actually even older than launchd. Prior to launchd the venerable inetd worked much like this: sockets were centrally created in a daemon that would start the actual service daemons passing the socket file descriptors during exec(). However the focus of inetd certainly wasn't local services, but Internet services (although later reimplementations supported AF\_UNIX sockets, too). It also wasn't a tool to parallelize boot-up or even useful for getting implicit dependencies right.

For TCP sockets inetd was primarily used in a way that for every incoming connection a new daemon instance was spawned. That meant that for each connection a new process was spawned and initialized, which is not a recipe for high-performance servers. However, right from the beginning inetd also supported another mode, where a single daemon was spawned on the first connection, and that single instance would then go on and also accept the follow-up connections (that's what the wait/nowait option in inetd.conf was for, a particularly badly documented option, unfortunately.) Per-connection daemon starts probably gave inetd its bad reputation for being slow. But that's not entirely fair.

好了，是时候暂停一下了，把你的咖啡加满，相信我，精彩会继续的。

首先，我们先澄清一些事实：上文所说这种思考逻辑是全新的吗？不，当然不是啦。类似的最著名的系统就是Apple的launchd system：在MacOS中，所有的daemon中的需要监听的socket被抽取出来，由launchd来完成。这个设计简直是太聪明了，这也是为何MacOS启动时间那么短的主要原因。这里可以向大家真心推荐一个[视频](https://www.youtube.com/watch?v=SjrtySM9Dns)，该视频讲述了launchd那帮家伙是如何做的。很不幸，这么好的idea并没有被Apple阵营之外的其他系统采用。

这个思路其实比launchd还要早，在launchd之前，超级服务程序inetd就是这样工作的：实际上用于通信的socket是在inetd中创建出来的，然后在exec的时候，将socket file descriptor传递给实际的service daemon。当然了，inetd的焦点并非本地服务，而是internet service（注：后来的inetd实现也支持了domain socket），而且它也不是一种并行化启动过程的工具，对于正确的处理依赖关系也没有什么帮助。

对于TCP socket而已，inetd主要是这样使用的：对于每一个来的连接请求，inetd都会实例化一个daemon（fork一个进程，exec之，然后初始化）来处理，对于高性能服务器而言，这种方法是不可接受的。不过，其实从一开始，inetd就支持另外一种mode，在这种mode下，只会在第一次连接的时候实例化一个daemon进程，并且该进程会随后处理后续来的请求。（也就是inetd.conf中的wait/nowait选项的含义了，不过很不幸，文档中关于该option的描述太差了）。per-connection的daemon进程大概就是大家诟病inetd速度太慢的原因吧，其实这有些不公平。

**Parallelizing Bus Services**

Modern daemons on Linux tend to provide services via D-Bus instead of plain AF\_UNIX sockets. Now, the question is, for those services, can we apply the same parallelizing boot logic as for traditional socket services? Yes, we can, D-Bus already has all the right hooks for it: using bus activation a service can be started the first time it is accessed. Bus activation also gives us the minimal per-request synchronisation we need for starting up the providers and the consumers of D-Bus services at the same time: if we want to start Avahi at the same time as CUPS (side note: CUPS uses Avahi to browse for mDNS/DNS-SD printers), then we can simply run them at the same time, and if CUPS is quicker than Avahi via the bus activation logic we can get D-Bus to queue the request until Avahi manages to establish its service name.

So, in summary: the socket-based service activation and the bus-based service activation together enable us to start **all** daemons in parallel, without any further synchronization. Activation also allows us to do lazy-loading of services: if a service is rarely used, we can just load it the first time somebody accesses the socket or bus name, instead of starting it during boot.

And if that's not great, then I don't **know** what is great!

**并行化各种bus service**

现在的Linux下的daemon进程倾向于通过D-Bus而不是domain socket来提供服务。因此，问题来了：对于这些service，我们能够应用同样的思考逻辑吗？在上面的描述中，我们通过解除soket依赖而尽可能的在启动阶段并行化执行各种service，当场景转换到D-Bus的情况下，同样的逻辑思考还有效吗？没有问题，D-Bus已经提供了相应的机制了：利用bus message来激活service。也就是说当client通过D-Bus的接口来请求服务的时候，该服务会启动执行，并且处理client的请求。这种bus activation的机制降低了D-Bus总线服务提供进程（provider）和服务使用进程（consumer）之间的同步需求，为provider和consumer并行启动创造了条件。举一个实际的例子：比如说我们想要Avahi和CUPS这两个daemon同时启动（注意：CPUS需要Avahi的服务来浏览支持mDNS/DNS-SD的打印机）。由于bus activation，CUPS会比Avahi启动的快一些，在这种情况下，D-BUS可以对CUPS的请求进行排队，直到Avahi建立自己的service name。

因此，最后总结如下：通过socket激活服务以及通过bus request激活服务组合起来，可以让我们并行执行所有的daemons，而不需要特别的同步机制。按需激活服务也提供了一种延迟加载服务（lazy-loading）的机制：如果该服务很少使用，那么我们可以在用户首次通过socket或者bus name来访问请求服务的时候加载该daemon，而不是一开始就启动起来。

如果你觉得这种方法不够帅，那么我也不知道什么是真正的帅了。

**Parallelizing File System Jobs**

If you look [at the serialization graphs of the boot process](http://picasaweb.google.com/betsubetsu43/Fedora#5179125455943690130) of current distributions, there are more synchronisation points than just daemon start-ups: most prominently there are file-system related jobs: mounting, fscking, quota. Right now, on boot-up a lot of time is spent idling to wait until all devices that are listed in /etc/fstab show up in the device tree and are then fsck'ed, mounted, quota checked (if enabled). Only after that is fully finished we go on and boot the actual services.

Can we improve this? It turns out we can. Harald Hoyer came up with the idea of using the venerable autofs system for this:

Just like a connect() call shows that a service is interested in another service, an open() (or a similar call) shows that a service is interested in a specific file or file-system. So, in order to improve how much we can parallelize we can make those apps wait only if a file-system they are looking for is not yet mounted and readily available: we set up an autofs mount point, and then when our file-system finished fsck and quota due to normal boot-up we replace it by the real mount. While the file-system is not ready yet, the access will be queued by the kernel and the accessing process will block, but only that one daemon and only that one access. And this way we can begin starting our daemons even before all file systems have been fully made available -- without them missing any files, and maximizing parallelization.

Parallelizing file system jobs and service jobs does not make sense for /, after all that's where the service binaries are usually stored. However, for file-systems such as /home, that usually are bigger, even encrypted, possibly remote and seldom accessed by the usual boot-up daemons, this can improve boot time considerably. It is probably not necessary to mention this, but virtual file systems, such as procfs or sysfs should never be mounted via autofs.

**并行化文件系统的任务**

如果你仔细看看目前的各种linux发行版的串行启动过程图的话，你就会发现，并非只有daemon启动的时候需要同步机制，占主导地位的是一些和文件系统操作相关的同步点：mount文件系统，check文件系统，文件系统配额检查等。现在，很大一部的启动时间是都是不断的在等待/etc/fstab中的设备节点出现在文件系统的/dev目录下，一旦检测到设备节点ready之后，就可以执行mount、fscheck、配额检查等等。在这些任务完成之后，才会真正启动各种service。

能不能优化这些文件系统的操作？看起来应该是可以的，Harald Hoyer想了一个主意，也就是传说中的autofs系统来进行启动阶段的文件系统任务的优化：

daemon进程中的一个connect()函数调用实际上反应的是对另外一个 daemon进程的服务需求。同样的，一个daemon进程中的open()函数调用，反应的是该daemon对文件系统特定文件的需求。因此，为了更大的并行化，我们可以让这些应用程序只有在访问一个尚未挂载的文件系统的时候进入等待状态。不过，不会等太久，因为通过设定autofs mount point，该文件系统可以很容易变得唾手可得。在正常启动过程中，当我们的文件系统完成那些check和配额检查之后，我们可以用真实的mount后的文件系统挂载点来代替之前的那个autofs mount point。在文件系统还没有真正ready之前，所有的访问会被内核保存在队列中，而发起访问的进程会被阻塞，不过阻塞的只是那一个daemon进程，那一次文件访问。通过这种机制，我们可以一开始就启动所有的daemon，甚至是文件系统还没有完全的ready，从而尽可能的让启动过程并行化。

在我们尽可能并行化各种系统启动阶段的任务的时候（包括文件系统任务和启动各种daemon任务），根目录“/”是一个特例，它必须要首先ready（解除对“/”目录的依赖是没有意义的），毕竟各种service的二进制程序是保存在/目录下面的。然而，对于象/home这样的文件系统，它们都会比较大，甚至是加密的，也许是文件存储介质在远端，并且基本上也不会被启动阶段的daemon访问。解除这些文件系统的依赖可以大大缩短系统启动时间。当然，也许不必提醒大家，那些虚拟文件系统，例如procfs或者sysfs应该永远不要通过autofs来加载。

I wouldn't be surprised if some readers might find integrating autofs in an init system a bit fragile and even weird, and maybe more on the "crackish" side of things. However, having played around with this extensively I can tell you that this actually feels quite right. Using autofs here simply means that we can create a mount point without having to provide the backing file system right-away. In effect it hence only delays accesses. If an application tries to access an autofs file-system and we take very long to replace it with the real file-system, it will hang in an interruptible sleep, meaning that you can safely cancel it, for example via C-c. Also note that at any point, if the mount point should not be mountable in the end (maybe because fsck failed), we can just tell autofs to return a clean error code (like ENOENT). So, I guess what I want to say is that even though integrating autofs into an init system might appear adventurous at first, our experimental code has shown that this idea works surprisingly well in practice -- if it is done for the right reasons and the right way.

Also note that these should be *direct* autofs mounts, meaning that from an application perspective there's little effective difference between a classic mount point and one based on autofs.

不少读者发现systemd这个新的init系统集成了autofs的功能，他们觉得这样的设计非常古怪，会让init系统变得脆弱，甚至觉得这样的设计令人厌恶的。如果他们这么想，我也不会觉得奇怪，毕竟传统的unix艺术是do one thing and do it well。不过，在我深入参与这件事情并且不断的使用这个机制之后，我可以说我们的思路是正确的。在这里使用autofs也就是意味着我们能够在无法立刻提供后备文件系统的情况下，创建一个挂载点。因而实际的效果只不过就是延迟了对文件的访问。如果一个应用程序试图去访问一个autofs的文件系统，并且我们会花费很长的时间来用真正的文件系统来代替那个autofs的文件系统。那么该应用程序将会进入不可被信号中断的状态，也就意味着你不能安全的干掉它，比如通过Control-c。还有一点需要注意，如果最后发现该文件系统无法挂载（例如：fsck failed），我们可以告诉autofs返回一个clean error code（类似ENOENT）。因此，最后我想说的是：尽管在开始的时候感觉将autofs集成到init system是一个很冒险的想法，在经过实践的检验，我们的代码已经证明了这个想法工作的相当的好，这也就说明了我们合理的做事情，走在正确的道路上。

**Keeping the First User PID Small**

Another thing we can learn from the MacOS boot-up logic is that shell scripts are evil. Shell is fast and shell is slow. It is fast to hack, but slow in execution. The classic sysvinit boot logic is modelled around shell scripts. Whether it is /bin/bash or any other shell (that was written to make shell scripts faster), in the end the approach is doomed to be slow. On my system the scripts in /etc/init.d call grep at least 77 times. awk is called 92 times, cut 23 and sed 74. Every time those commands (and others) are called, a process is spawned, the libraries searched, some start-up stuff like i18n and so on set up and more. And then after seldom doing more than a trivial string operation the process is terminated again. Of course, that has to be incredibly slow. No other language but shell would do something like that. On top of that, shell scripts are also very fragile, and change their behaviour drastically based on environment variables and suchlike, stuff that is hard to oversee and control.

So, let's get rid of shell scripts in the boot process! Before we can do that we need to figure out what they are currently actually used for: well, the big picture is that most of the time, what they do is actually quite boring. Most of the scripting is spent on trivial setup and tear-down of services, and should be rewritten in C, either in separate executables, or moved into the daemons themselves, or simply be done in the init system.

It is not likely that we can get rid of shell scripts during system boot-up entirely anytime soon. Rewriting them in C takes time, in a few case does not really make sense, and sometimes shell scripts are just too handy to do without. But we can certainly make them less prominent.

A good metric for measuring shell script infestation of the boot process is the PID number of the first process you can start after the system is fully booted up. Boot up, log in, open a terminal, and type echo $$. Try that on your Linux system, and then compare the result with MacOS! (Hint, it's something like this: Linux PID 1823; MacOS PID 154, measured on test systems we own.)

**让第一个用户进程PID值小一些**

另外一个从MacOS启动过程中学到的事情就是：shell脚本是魔鬼。shell脚本非常快，也非常的慢。它可以非常容易非常快的hack，但是执行的时候非常的慢。经典的SysVinit的启动逻辑就是构建在shell脚本之上的，具体的脚本可能是/bin/bash或者其他的优化过的shell，但是最终这种基于shell的启动逻辑注定是速度非常的慢。在我的系统中，/etc/init.d目录下的脚本调用grep至少77次，调用awk 92次，调用cut 23次，调用sed 74次。每一次这些命令（也许是其他形式）被调用，fork进程，exec进程，搜索libs，还有一些类似i18n的设定啊什么的。而这么兴师动众之后，实际的操作不过就是简单的字符操作而已，完成之后，进程被销毁。这一切导致的启动过程异常的慢，我相信只有脚本能够达到这个效果，其他的任何语言都做不到。更重要的是，shell脚本非常的脆弱，通过改变环境变量就可以完全改变其行为，这样的类似的事情很难监督和控制。

因此，我们的决定就是在系统启动过程中减少脚本的使用。在进行这一步之前，我们首先要搞清楚目前用脚本是来干什么的。OK，从大的层面来说，脚本大部分时间都是在做一些无聊的事情。大部分的脚本都是在做一些简单的setup service或者tear-down service的动作，而这些都应该用c来重写，具体可以放到各自可执行文件中，或者移入daemon的实现中，或者更简单些，把这些任务交给init system。

很快的将shell脚本从启动过程中抹去也不太现实，毕竟用c重写需要花费一些时间，此外，在有些场合下，用c代替脚本没有意义，其实有的时候脚本用起来挺方便，但是，我们肯定不能让它在启动过程中占据主导地位。

有一个简单的度量shell脚本在启动过程中的肆虐程度的方法就是看看系统完成启动之后创建的第一个进程的PID。方法很简单，启动之后，登录系统，打开终端，输入echo $$。看看你的系统输出怎样的结果，再对比MacOS，你就会明白一切了（提示：对比结果大致如下：Linux PID 1823，MacOS PID 154，这是我的系统上的测试结果）

**Keeping Track of Processes**

A central part of a system that starts up and maintains services should be process babysitting: it should watch services. Restart them if they shut down. If they crash it should collect information about them, and keep it around for the administrator, and cross-link that information with what is available from crash dump systems such as abrt, and in logging systems like syslog or the audit system.

It should also be capable of shutting down a service completely. That might sound easy, but is harder than you think. Traditionally on Unix a process that does double-forking can escape the supervision of its parent, and the old parent will not learn about the relation of the new process to the one it actually started. An example: currently, a misbehaving CGI script that has double-forked is not terminated when you shut down Apache. Furthermore, you will not even be able to figure out its relation to Apache, unless you know it by name and purpose.

So, how can we keep track of processes, so that they cannot escape the babysitter, and that we can control them as one unit even if they fork a gazillion times?

Different people came up with different solutions for this. I am not going into much detail here, but let's at least say that approaches based on ptrace or the netlink connector (a kernel interface which allows you to get a netlink message each time any process on the system fork()s or exit()s) that some people have investigated and implemented, have been criticised as ugly and not very scalable.

So what can we do about this? Well, since quite a while the kernel knows [Control Groups](http://git.kernel.org/gitweb.cgi?p=linux/kernel/git/torvalds/linux-2.6.git;a=blob;f=Documentation/cgroups/cgroups.txt;hb=HEAD) (aka "cgroups"). Basically they allow the creation of a hierarchy of groups of processes. The hierarchy is directly exposed in a virtual file-system, and hence easily accessible. The group names are basically directory names in that file-system. If a process belonging to a specific cgroup fork()s, its child will become a member of the same group. Unless it is privileged and has access to the cgroup file system it cannot escape its group. Originally, cgroups have been introduced into the kernel for the purpose of containers: certain kernel subsystems can enforce limits on resources of certain groups, such as limiting CPU or memory usage. Traditional resource limits (as implemented by setrlimit()) are (mostly) per-process. cgroups on the other hand let you enforce limits on entire groups of processes. cgroups are also useful to enforce limits outside of the immediate container use case. You can use it for example to limit the total amount of memory or CPU Apache and all its children may use. Then, a misbehaving CGI script can no longer escape your setrlimit() resource control by simply forking away.

In addition to container and resource limit enforcement cgroups are very useful to keep track of daemons: cgroup membership is securely inherited by child processes, they cannot escape. There's a notification system available so that a supervisor process can be notified when a cgroup runs empty. You can find the cgroups of a process by reading /proc/$PID/cgroup. cgroups hence make a very good choice to keep track of processes for babysitting purposes.

**跟踪进程关系**

init系统软件会启动各种service进程并对其进行维护，最主要的部分是对service进程的监控：init进程需要随时监控service的状态，如果该service被shutdown，那么init负责将其restart，如果service crash了，init进程需要收集必要的信息并让系统管理员了解具体的情况，同时把这些信息和从crash dump系统（例如abrt）以及从log系统中（例如syslog）或者audit系统中获取的信息进行连接。

init系统软件可以shutdown一个service进程，这听起来很容易，但是其实比你想象的要难一些。对于传统的Unix，一个进行了两次fork的进程能逃脱其父进程的监视（A fork了B进程后，B是A的子进程因此A可以对其进行管理，如果B又进行fork，产生B1进程，同时B进程退出，这时候B1的父进程是init进程，因此也就逃脱了A进程的魔掌）。并且在这种情况下，最早的那个父进程（例子中的A进程）并不知道这个新进程（指B1进程）和fork它的B进程之间的关系。举一个实际的例子：现在，一个行为诡异的CGI脚本在经历两次fork之后，已经脱离了Apache的关系，因此即便我们shutdown了Apache服务进程，该CGI脚本进程仍然存在。甚至，你根本不知道它和Apache的关系，除非你通过名字或者它的功能。

因此，问题来了，我们怎么来跟踪进程关系呢？我们怎样才能让进程在fork多次之后仍然无法逃脱init进程的控制呢？

对于这个问题，不同的人采用了不同的方法。这里，我也不会细说，不过至少了解到有一个基于ptrace或者netlink connector的方法有人正在研究并且给出了实现，当然，这种方法被批评说是扩展性不好，很丑陋。

那么我们采用什么方法呢？答案就是Control Group（也就是内核中的cgroups子系统）。概括的说cgroups是一种能够创建一组进程层次关系的方法。而进程的层次关系是通过虚拟文件系统体现出来的，因此，很容易使用。group name就是虚拟文件系统的目录名字。如果一个属于特定cgroup的进程执行fork操作，它的子进程也是属于该group的成员。除非该进程有访问cgroup文件系统的权限，否则该进程无法逃脱这个cgroup。刚开始，内核为了支持container的概念而引入了cgroup：某个内核子系统可以限制指定group的资源使用上限。例如CPU或者memory的使用上限。传统的resource limit机制是per-process的。cgroup可以实现对一组进程的资源使用进行限制，也可以对一个container之外对象进行资源使用的限制。举一个例子，例如你可以把Apache极其fork的子进程放入一个group，并且限定他们使用的memory。这时候，行为不端的CGI脚本进程是不可能通过fork来逃脱你对这一组进程的资源限制。

除了container以及资源限制，cgroup在跟踪daemon进程关系上也很有用：处于安全的考量，cgroup的关系会被子进程继承，也就是说子进程无法逃离出cgroup。当整个cgroup为空的时候，会有通知机制来通知监控进程。进程本身也可以通过/proc/$PID/cgroup来获取本cgroup进程的信息。因此，cgroup是跟踪进程关系，执行监控的很好的方法。

**Controlling the Process Execution Environment**

A good babysitter should not only oversee and control when a daemon starts, ends or crashes, but also set up a good, minimal, and secure working environment for it.

That means setting obvious process parameters such as the setrlimit() resource limits, user/group IDs or the environment block, but does not end there. The Linux kernel gives users and administrators a lot of control over processes (some of it is rarely used, currently). For each process you can set CPU and IO scheduler controls, the capability bounding set, CPU affinity or of course cgroup environments with additional limits, and more.

As an example, ioprio\_set() with IOPRIO\_CLASS\_IDLE is a great away to minimize the effect of locate's updatedb on system interactivity.

On top of that certain high-level controls can be very useful, such as setting up read-only file system overlays based on read-only bind mounts. That way one can run certain daemons so that all (or some) file systems appear read-only to them, so that EROFS is returned on every write request. As such this can be used to lock down what daemons can do similar in fashion to a poor man's SELinux policy system (but this certainly doesn't replace SELinux, don't get any bad ideas, please).

Finally logging is an important part of executing services: ideally every bit of output a service generates should be logged away. An init system should hence provide logging to daemons it spawns right from the beginning, and connect stdout and stderr to syslog or in some cases even /dev/kmsg which in many cases makes a very useful replacement for syslog (embedded folks, listen up!), especially in times where the kernel log buffer is configured ridiculously large out-of-the-box.

一个好的daemon监控师不能只是照看和控制daemon的启动、停止、收集crash信息什么的，也需要为daemon设立好其执行环境，至少需要是安全的执行环境。

具体来讲呢就是设定进程的各种参数，例如：资源限制参数（setrlimit函数）、User/group ID或者是环境变量块等等。Linux kernel提供了很多的接口可以让用户或者管理员对进程进行设定（当然，有些控制很少被用到）。对于每一个进程，你可以设定CPU或者IO scheduler的参数，设定capability bounding set的参数，设定CPU affinity参数，或者设定cgroup环境参数来附加更多的资源控制。这样的参数还有很多很多。

举一个例子：通过ioprio\_set将sheduling class设置为IOPRIO\_CLASS\_IDLE，这样的设定可以最大程度的降低updatedb（locate命令需要他的协助）对系统交互性的影响。

这些高级别的控制是非常的有用的，比如我们想让某个daemon进程以只读的方式访问某个文件系统的全部（或者部分）文件，一旦该daemon进程对这些文件进行写入将返回EROFS错误码。整个将文件系统mount成read only可不可以呢？不行，其他daemon需要是R/W的，那怎么办呢？可以考虑使用read only的bind mount（--bind参数）。通过这种方式，可以限定一个具体daemon的行为。这个有点类似低配置版本的SELinux策略系统（注意，不要试图替代SELinux，不要从我这get错误的技能，^\_^）

最后，我们来说说日志。日志是一个执行服务进程的重要组成部分：理想的日志是应该记录service每一个输出的bit到日志系统中去。因此，既然init系统软件启动了service进程，那么就需要负责从一开始就为service提供日志服务，把service进程的stdout和stderr连接到syslog或者在某些特例下，连接到/dev/kmsg。把service的日志输入通过/dev/kmsg输入到kernel log buffer，是不是有点脑洞大开的感觉，不过在很多场合下，这是替换syslog的不错的方法（搞嵌入的家伙们，耳朵竖起来），特别是那些kernel log buffer配置的大的吓人的场景。

**On Upstart**

To begin with, let me emphasize that I actually like the code of Upstart, it is very well commented and easy to follow. It's certainly something other projects should learn from (including my own).

That being said, I can't say I agree with the general approach of Upstart. But first, a bit more about the project:

Upstart does not share code with sysvinit, and its functionality is a super-set of it, and provides compatibility to some degree with the well known SysV init scripts. It's main feature is its event-based approach: starting and stopping of processes is bound to "events" happening in the system, where an "event" can be a lot of different things, such as: a network interfaces becomes available or some other software has been started.

Upstart does service serialization via these events: if the syslog-started event is triggered this is used as an indication to start D-Bus since it can now make use of Syslog. And then, when dbus-started is triggered, NetworkManager is started, since it may now use D-Bus, and so on.

One could say that this way the actual logical dependency tree that exists and is understood by the admin or developer is translated and encoded into event and action rules: every logical "a needs b" rule that the administrator/developer is aware of becomes a "start a when b is started" plus "stop a when b is stopped". In some way this certainly is a simplification: especially for the code in Upstart itself. However I would argue that this simplification is actually detrimental. First of all, the logical dependency system does not go away, the person who is writing Upstart files must now translate the dependencies manually into these event/action rules (actually, two rules for each dependency). So, instead of letting the computer figure out what to do based on the dependencies, the user has to manually translate the dependencies into simple event/action rules. Also, because the dependency information has never been encoded it is not available at runtime, effectively meaning that an administrator who tries to figure our *why* something happened, i.e. why a is started when b is started, has no chance of finding that out.

**关于Upstart**

首先，我必须强调一下：我非常喜欢Upstart的代码，注释非常好，代码很容易理解。其他的开源项目真实应该好好学习Upstart（当然也包括我自己）

虽然欣赏Upstart的代码风格，但是我其实不是非常赞同其基本的设计思路。当然，批判之前先介绍一下它：

Upstart并不和sysVinit共享代码，而其Upstart的功能完全覆盖了sysVinit，为了兼容性，Upstart也某种程度支持了sysV init script。Upstart的主要特点是事件驱动，启动或者停止进程都是绑定系统中发生的某些事件。具体的事件可以是各种各样的，例如：网卡已经进入工作状态或者一些软件已经启动了。

Upstart是通过系统发生的事件做为驱动，来串行化的启动各种service，例如：如果syslog-started事件到来，那么这表示D-Bus需要被启动起来了，因为D-Bus需要syslog的服务。一旦D-BUS daemon运行起来，也就触发了dbus-started事件，这时候NetworkManager就启动起来了，因为它可以访问D-Bus了。

我们也可以这么说，被系统管理员和开发者所理解的各个组件的逻辑依赖关系，被Upstart翻译成事件-动作的规则：每一个“a组件需要b组件”的逻辑（从系统管理员或者开发者角度看）变成“如果b组件启动，那么启动a组件”“如果b组件停止，那么a组件也需要停止”的逻辑。从某些角度看，这也是一种简化：特别是对于Upstart的代码而言。但是，我认为这种简化是有害的。首先，这些逻辑依赖关系并没有消失，写Upstart file的人需要将这些依赖关系翻译成event/action规则（实际上每一个依赖关系需要2条规则），因此，本质上应该有计算机来自行分辨的依赖关系，在Upstart中仍然需要用户手动去翻译成各种event/action规则。还有，由于真正的依赖信息并没有给出，因此运行时候这些依赖关系也是无法获得的，实际上这也就意味着系统管理员实际上并不知道是具体是怎么回事：他只是知道“如果b组件启动，那么启动a组件”，但是并不知道为什么a组件要随着b组件的启动而启动（中国俗语就是：知其然不知其所以然）。

Furthermore, the event logic turns around all dependencies, from the feet onto their head. Instead of *minimizing* the amount of work (which is something that a good init system should focus on, as pointed out in the beginning of this blog story), it actually *maximizes* the amount of work to do during operations. Or in other words, instead of having a clear goal and only doing the things it really needs to do to reach the goal, it does one step, and then after finishing it, it does **all** steps that possibly could follow it.

Or to put it simpler: the fact that the user just started D-Bus is in no way an indication that NetworkManager should be started too (but this is what Upstart would do). It's right the other way round: when the user asks for NetworkManager, that is definitely an indication that D-Bus should be started too (which is certainly what most users would expect, right?).

A good init system should start only what is needed, and that on-demand. Either lazily or parallelized and in advance. However it should not start more than necessary, particularly not everything installed that could use that service.

Finally, I fail to see the actual usefulness of the event logic. It appears to me that most events that are exposed in Upstart actually are not punctual in nature, but have duration: a service starts, is running, and stops. A device is plugged in, is available, and is plugged out again. A mount point is in the process of being mounted, is fully mounted, or is being unmounted. A power plug is plugged in, the system runs on AC, and the power plug is pulled. Only a minority of the events an init system or process supervisor should handle are actually punctual, most of them are tuples of start, condition, and stop. This information is again not available in Upstart, because it focuses in singular events, and ignores durable dependencies.

更重要的是：事件驱动逻辑思考颠倒了所有的依赖关系，从头到脚，彻底了颠倒了依赖关系。Upstart实际上并没有减少工作（这一点是每一个优秀的init系统软件必须要关注的，就像本文前面说的），反而把要启动阶段要做的事情最大化了。换句话说，Upstart并没有一个清晰的目标，并且围绕着这个目标展开工作，Upstart的做法是执行了某一个组件A，然后把所有使用A组件服务的组件都运行起来。

我们用更具体的例子来说明一下：实际上，用户启动了D-Bus的服务实际上并不意味着他想要启动NetworkManager，但这确实Upstart想要做的。实际上，正确的思路应该是这样的：如果用户要求启动NetworkManager服务，那么其实也就是意味着D-Bus服务必须要启动（这不是大多数用户所期待的那样吗？）。

一个好的init系统软件应该只启动需要的组件，以及被请求的组件，或是lazy loading，或是并行执行组件。当然，好的init系统软件不能启动一些不需要的组件，特别是不能一个service启动了，那么就启动所有用户已经安装的，使用该服务的组件。

最后，我其实看不出来事件驱动逻辑有什么用处。对我来说，在Upstart中处理的各种事件在实际环境中并不是点状的，而是持续一段事件。例如：一个服务启动了，处于运行状态，然后又停止了。一个设备被插入，可以使用了，然后又被拔出。一个挂载点正在被mount过程中，完成了mount操作，然后又umount了。AC adapter插入，系统在AC电源供电的情况下运行，AC adapter被拔出了。在init系统监控系统行为过程中，只有很少的一些事件是点状的，大部分都是（启动，条件，停止）三元组。这些信息在Upstart中也都是无法知晓的，主要是因为它把注意力都放在单一事件上而忽略了持续性的依赖关系。

Now, I am aware that some of the issues I pointed out above are in some way mitigated by certain more recent changes in Upstart, particularly condition based syntaxes such as start on (local-filesystems and net-device-up IFACE=lo) in Upstart rule files. However, to me this appears mostly as an attempt to fix a system whose core design is flawed.

Besides that Upstart does OK for babysitting daemons, even though some choices might be questionable (see above), and there are certainly a lot of missed opportunities (see above, too).

There are other init systems besides sysvinit, Upstart and launchd. Most of them offer little substantial more than Upstart or sysvinit. The most interesting other contender is Solaris SMF, which supports proper dependencies between services. However, in many ways it is overly complex and, let's say, a bit *academic* with its excessive use of XML and new terminology for known things. It is also closely bound to Solaris specific features such as the *contract* system.

现在，我也有注意到Upstart的一些代码改动，我上面说的这个项目的一些缺陷已经被修复，特别是规则文件中基于某些条件的语法 ，例如start on(local-filesystems and net-device-up IFACE=lo)。不过，对我而言，这些修复不过是在一个有核心设计缺陷的系统中打补丁而已。

此外，Upstart在监控daemon进程上做的不错，尽管有些设计选择存在可疑之处（参考上文），它也是有很多错过的机会（参考上文）。

除了sysVinit、Upstart和launchd之外还有很多其他的init系统，不过“料”都不如Upstart或者SysVinit多。这里面最有意思的竞争者是Solaris SMF，它也支持service之间的依赖关系。不过具体的方法非常的复杂，而且有浓浓的“学术”的味道，它大量的使用了XML，而且为一些大家熟悉的东西定义了新的术语（言外之意是有点画蛇添足）。此外，SMF和Solaris系统的某些特性（例如contract system）捆绑的很紧。

**Putting it All Together: systemd**

Well, this is another good time for a little pause, because after I have hopefully explained above what I think a good PID 1 should be doing and what the current most used system does, we'll now come to where the beef is. So, go and refill you coffee mug again. It's going to be worth it.

You probably guessed it: what I suggested above as requirements and features for an ideal init system is actually available now, in a (still experimental) init system called systemd, and which I hereby want to announce. [Again, here's the code.](http://git.0pointer.de/?p=systemd.git) And here's a quick rundown of its features, and the rationale behind them:

systemd starts up and supervises the entire system (hence the name...). It implements all of the features pointed out above and a few more. It is based around the notion of *units*. Units have a name and a type. Since their configuration is usually loaded directly from the file system, these unit names are actually file names. Example: a unit avahi.service is read from a configuration file by the same name, and of course could be a unit encapsulating the Avahi daemon. There are several kinds of units:

**Putting it All Together：systemd**

好了，又到了休息一下的时间了。在上面的文章中，我希望已经把我对PID 1进程的思考（好的PID 1进程应该做什么）写出来了，此外，还谈了谈我对目前使用的init系统软件的看法，经过上面的开胃小菜铺垫之后，我们现在来看看”牛肉大餐“在哪里。请继续加满你的咖啡，且听我慢慢道来。

相信你已经猜到了：上面我关于一个理想的init系统软件的需求分析和功能列表的定义其实已经有了具体的实现了，这个全新的init系统软件就是systemd。再强调一次，代码在这里：[https://github.com/systemd/systemd](https://github.com/systemd/systemd "https://github.com/systemd/systemd")。本章我们会很快的介绍一下systemd的功能以及该功能背后的逻辑。

systemd启动起来并且监控整个系统（就像它的名字一样，system daemon），实现了上文所说的所有功能（当然也有一些其他的功能没有提及）。要理解systemd，首先要理解unit这个概念。Unit有自己的名字和类型，由于Unit的配置都是通常来自文件系统，因此unit的名字实际上就是文件的名字。例如：avahi.service就是一个unit，通过unit name可以从文件系统中加载该unit的配置文件，文件名同unit name。通过名字就可以知道，avahi.service应该是对avahi daemon的封装。systemd中有好几种unit，如下：

1. service: these are the most obvious kind of unit: daemons that can be started, stopped, restarted, reloaded. For compatibility with SysV we not only support our own configuration files for services, but also are able to read classic SysV init scripts, in particular we parse the LSB header, if it exists. /etc/init.d is hence not much more than just another source of configuration.
2. socket: this unit encapsulates a socket in the file-system or on the Internet. We currently support AF\_INET, AF\_INET6, AF\_UNIX sockets of the types stream, datagram, and sequential packet. We also support classic FIFOs as transport. Each socket unit has a matching service unit, that is started if the first connection comes in on the socket or FIFO. Example: nscd.socket starts nscd.service on an incoming connection.
3. device: this unit encapsulates a device in the Linux device tree. If a device is marked for this via udev rules, it will be exposed as a device unit in systemd. Properties set with udev can be used as configuration source to set dependencies for device units.
4. mount: this unit encapsulates a mount point in the file system hierarchy. systemd monitors all mount points how they come and go, and can also be used to mount or unmount mount-points. /etc/fstab is used here as an additional configuration source for these mount points, similar to how SysV init scripts can be used as additional configuration source for service units.
5. automount: this unit type encapsulates an automount point in the file system hierarchy. Each automount unit has a matching mount unit, which is started (i.e. mounted) as soon as the automount directory is accessed.
6. target: this unit type is used for logical grouping of units: instead of actually doing anything by itself it simply references other units, which thereby can be controlled together. Examples for this are: multi-user.target, which is a target that basically plays the role of run-level 5 on classic SysV system, or bluetooth.target which is requested as soon as a bluetooth dongle becomes available and which simply pulls in bluetooth related services that otherwise would not need to be started: bluetoothd and obexd and suchlike.
7. snapshot: similar to target units snapshots do not actually do anything themselves and their only purpose is to reference other units. Snapshots can be used to save/rollback the state of all services and units of the init system. Primarily it has two intended use cases: to allow the user to temporarily enter a specific state such as "Emergency Shell", terminating current services, and provide an easy way to return to the state before, pulling up all services again that got temporarily pulled down. And to ease support for system suspending: still many services cannot correctly deal with system suspend, and it is often a better idea to shut them down before suspend, and restore them afterwards.

（1）service。这是最常见的一种unit，主要用于daemon的启动、停止、restart以及reload。为了和SysV兼容，我们不仅支持systemd自己的service配置文件，而且也支持经典的SysV init scripts（systemd会读入sysV init script文件并且分析LSB header，当然，前提是该脚本文件存在）。因此，/etc/init.d目录其实也是systemd的配置文件目录。

（2）socket。这种unit封装了文件系统中的socket或者internet中的socket。目前我们支持AF\_INET, AF\_INET6, AF\_UNIX socket，数据包的类型可以是steam、datagram或者sequential packet。当然，我们也支持传统的FIFO（named pipe）做为通信管道。每一个socket unit都有一个service unit与之匹配，如果从这个socket（或者FIFO）首次收到连接请求，那么systemd启动其对应的service。例如当收到第一个连接请求后，nscd.socket会启动nscd.service。

（3）device。这种unit封装了Linux系统中的一个设备。如果一个device在其对应的udev rules有特殊的标记，那么在systemd系统中，该设备会形成一个device unit，同时，在udev规则文件中的属性可以变成systemd unit file中依赖关系配置。

（4）mount。这种unit封装了文件系统中的挂载点。systemd会监控系统中所有的挂载点的来去，也会自动的mount或者umount unit file里面定义的挂载点。除了各种mount unit 配置文件，/etc/fstab也是挂载点的输入源（主要是考虑兼容性），这个概念类似service中的SysV init scripts。

（5）automount。这种unit封装了文件系统中的自动挂载点。每一个automount unit都有一个匹配的mount unit，一旦automount定义的目录被访问了，那么systemd就会执行对应的mount unit。

（6）target。这种unit主要是用于对各种unit进行逻辑分组。target unit本身没有什么具体的事情要做，它仅仅是引用了若干其他的unit，而通过对target unit的控制达到控制该target所属的那一组unit的行为。例如：multi-user.target，这个target基本上是实现了传统SysV的run-level 5的功能。而bluetooth.target，该target在bluetooth dongle插入系统并且ready之后会被激活，从而将蓝牙相关的服务（bluetoothd或者obexd等等）启动起来。

（7）snapshot。和target类似，snapshot也没有什么实际功能，也只是引用了若干其他的unit。snapshot主要是用于init系统中所有service和unit状态的保存和回滚。snapshot主要有两个应用场景：一个是允许用户可以临时性的进入某个特定的状态，例如"Emergency Shell"。snapshot其实就是终止当前的service，然后回到之前的保存的某个系统状态上去。另外一个场景用于system suspending。目前仍然有很多service不能正确的处理system suspend，因此可以考虑在system suspend之前shutdown service，然后在system resume的时候再恢复service。

后面的章节描述功能列表和项目状态，我觉得意义不太，大家有兴趣就自己看看吧。

*原创翻译文章，转发请注明出处。蜗窝科技*
