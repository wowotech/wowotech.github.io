---
title: "Linux时间子系统之（五）：POSIX Clock"
date: 2015-01-05T19:03:50+08:00
url: "/timer_subsystem/posix-clock.html"
gid: "137"
emlog_type: "blog"
summary: "clock是timer的基础，任何一个timer都需要运作在一个指定的clock上来。内核中维护了若干的clock，本文第二章描述了clock的 基本概念和一些静态定义的posix clock。根据计时的特点，clock分成两种：一种是真实世界的时间概念，另外一个是仅仅计算CPU执行时间 ，这两种clock分别在第三和第四章描述。从clock的生命周期来看，可以分成静态和动态的posix cloc"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["posix-clock"]
views: 40508
comment_count: 12
aliases:
  - "/timer_subsystem/137.html"
  - "/137.html"
---

一、前言

clock是timer的基础，任何一个timer都需要运作在一个指定的clock上来。内核中维护了若干的clock，本文第二章描述了clock的基本概念和一些静态定义的posix clock。根据计时的特点，clock分成两种：一种是真实世界的时间概念，另外一个是仅仅计算CPU执行时间 ，这两种clock分别在第三和第四章描述。从clock的生命周期来看，可以分成静态和动态的posix clock，静态是一直存在于内核中的，而动态clock有创建和销毁的概念，本文第五章描述了dynamic posix clock。

二、基本概念

1、核心数据结构

所谓clock，实际上就是一种计时工具，可能是硬件，也可能是软件，当然对于POSIX clock而言，当然是指软件抽象了。clock能够记录一段时间的流逝，这段时间可能是真实的墙上时间，也可能是虚拟的时间，例如基于某个进程或者线程的CPU执行时间。在linux kernel中，用struct k\_clock来抽象，具体定义如下：

> struct k\_clock {   
> int (\*clock\_getres) (const clockid\_t which\_clock, struct timespec \*tp);   
> int (\*clock\_set) (const clockid\_t which\_clock, const struct timespec \*tp);   
> int (\*clock\_get) (const clockid\_t which\_clock, struct timespec \* tp);   
> int (\*clock\_adj) (const clockid\_t which\_clock, struct timex \*tx);   
> int (\*timer\_create) (struct k\_itimer \*timer);   
> int (\*nsleep) (const clockid\_t which\_clock, int flags, struct timespec \*, struct timespec \_\_user \*);   
> long (\*nsleep\_restart) (struct restart\_block \*restart\_block);   
> int (\*timer\_set) (struct k\_itimer \* timr, int flags, struct itimerspec \* new\_setting,   
> struct itimerspec \* old\_setting);   
> int (\*timer\_del) (struct k\_itimer \* timr);   
> void (\*timer\_get) (struct k\_itimer \* timr, struct itimerspec \* cur\_setting);   
> };

clock作为一个计时工具当然有计时精度，通过clock\_getres函数可以获取该clock的时间精度，需要说明的是这个精度是和timer相关的，用于将用户设定的timer超时时间规整到clock精度允许的数值上。clock\_get和clock\_set函数可以分别获取和设定当前的时间，这个时间值是一个绝对时间值（对于时间轴而言，这个绝对时间也是相对的，是相对于该timeline的epoch而言），标记了当前时间点。clock计时有可能是不准确的，例如基于系统晶振的clock。一方面本身晶振的精度有限，时间累积长了会出现较大误差。另外，晶振也会随着使用时间的推移、温度的变化等等因素而导致误差。clock\_adj函数允许系统根据外部的精确时间信息对本clock进行调整。nsleep和nsleep\_restart这两个成员函数可以让进程sleep一段时间。timer\_xxx系列函数是和POSIX interval timer相关，具体会在POSIX timer文档中描述。

2、静态定义的clock

> static struct k\_clock posix\_clocks[MAX\_CLOCKS];

posix\_clocks数组定义了系统支持的所有的clock，相关的定义如下：

> #define CLOCK\_REALTIME 0   
> #define CLOCK\_MONOTONIC 1   
> #define CLOCK\_PROCESS\_CPUTIME\_ID 2   
> #define CLOCK\_THREAD\_CPUTIME\_ID 3   
> #define CLOCK\_MONOTONIC\_RAW 4   
> #define CLOCK\_REALTIME\_COARSE 5   
> #define CLOCK\_MONOTONIC\_COARSE 6   
> #define CLOCK\_BOOTTIME 7   
> #define CLOCK\_REALTIME\_ALARM 8   
> #define CLOCK\_BOOTTIME\_ALARM 9   
> #define CLOCK\_SGI\_CYCLE 10 /\* Hardware specific \*/   
> #define CLOCK\_TAI 11
>
> #define MAX\_CLOCKS 16

POSIX标准定义了4种类型的clock，CLOCK\_REALTIME、CLOCK\_MONOTONIC、CLOCK\_PROCESS\_CPUTIME\_ID和CLOCK\_THREAD\_CPUTIME\_ID，其他是linux specific。如果一个clock的timeline是基于CPU运行时间的，那么我们称之CPU-time clock。CPU-time clock主要是用来为某个进程或者线程的执行时间进行计时的，一旦线程（进程）被切换，那么该clock就停掉了，直到下次调度器切换回该线程（进程）执行。

各个具体的操作系统实现可以定义自己特有的clock，对于Linux kernel，我们定义了若干种clock。CLOCK\_MONOTONIC\_RAW启动时间点被设成0，此后一直不断累加，而且能设定，不会随NTP调整。CLOCK\_REALTIME\_COARSE、CLOCK\_MONOTONIC\_COARSE的概念和CLOCK\_REALTIME、CLOCK\_MONOTONIC的概念是类似的，只不过是精度是比较粗的版本。有时候，timer没有必要要求那么高的精度，那么我们可以使用这种clock，从而可以获取更好的性能。CLOCK\_BOOTTIME和CLOCK\_MONOTONIC类似，也是单调上述，在系统初始化的时候设定的基准数值是0，不过CLOCK\_BOOTTIME计算系统suspend的时间，也就是说，不论是running还是suspend（这些都算是启动时间），CLOCK\_BOOTTIME都会累积计时，直到系统reset或者shutdown。

CLOCK\_REALTIME\_ALARM和CLOCK\_BOOTTIME\_ALARM主要用于Alarmtimer，这种timer是基于RTC的，更详细的内容请参考本站Alarmtimer的文档。CLOCK\_TAI是原子钟的时间，和基于UTC的CLOCK\_REALTIME类似，不过没有leap second。

用户空间的clock\_xxx函数会传递clock id的参数，在内核态，根据id作为index在posix\_clocks数组中可以索引到对应的clock，然后调用clock对应的callback函数就OK了。当然基本意思就是这样，具体实现如下：

> static struct k\_clock \*clockid\_to\_kclock(const clockid\_t id)   
> {   
> if (id < 0)   
> return (id & CLOCKFD\_MASK) == CLOCKFD ?   
> &clock\_posix\_dynamic : &clock\_posix\_cpu;
>
> if (id >= MAX\_CLOCKS || !posix\_clocks[id].clock\_getres)   
> return NULL;   
> return &posix\_clocks[id];   
> }

clockid\_to\_kclock这个函数用来将clock id和具体的posix clock的k\_clock 数据结构对应起来。在linux平台上，clockid是int类型的数据，共32个bit，高29个bit用来保存一个pid（用于CPU-time clock）或者fd（动态分配的clock），bit 2用来说明该CPU-time clock是一个进程clock还是线程clock。bit 1和bit 0用来说明该clock id的类型：PROF=0, VIRT=1, SCHED=2, or FD=3。

当clock id小于0的时候，要么是CPU-time clock，要么是动态分配的clock，可以根据clock id的类型来判断。CPU-time clock和动态分配的clock后面会具体介绍。

三、各种real timeclock的定义

系统初始化的时候会调用init\_posix\_timers函数对各种静态定义的real time clock进行注册。注：monotonic clock也是real time clock的一种，全称是monotonic real time clock。

1、real time clock的定义如下（timer相关内容不在本文描述）：

> struct k\_clock clock\_realtime = {   
> .clock\_getres = hrtimer\_get\_res,   
> .clock\_get = posix\_clock\_realtime\_get,   
> .clock\_set = posix\_clock\_realtime\_set,   
> .clock\_adj = posix\_clock\_realtime\_adj,   
> .nsleep = common\_nsleep,   
> .nsleep\_restart = hrtimer\_nanosleep\_restart,   
> };

real time clock需要调用timekeeping模块的接口来获取和设定当前时间值。对于获取当前时间值的函数posix\_clock\_realtime\_get而言，是调用ktime\_get\_real\_ts函数，该函数是timekeeping模块的接口函数，以timespec的格式回了real time clock的当前值。posix\_clock\_realtime\_set函数主要是调用do\_settimeofday这个timekeeping模块的接口函数。posix\_clock\_realtime\_adj是调用do\_adjtimex接口函数来实现具体的功能。

纳秒级别的sleep是通过高精度timer实现的，real time clock的精度和hrtimer相关，具体可以参考hrtimer相关文档。

2、monotonic clock的定义如下：

> struct k\_clock clock\_monotonic = {   
> .clock\_getres = hrtimer\_get\_res,   
> .clock\_get = posix\_ktime\_get\_ts,   
> .nsleep = common\_nsleep,   
> .nsleep\_restart = hrtimer\_nanosleep\_restart,   
> };

monotonic clock没有clock\_set函数，不能被设定。通过ktime\_get\_ts这个timekeeping模块的接口可以获得monotonic clock的当前值。纳秒级别的sleep以及精度的获取函数和real time clock一样。

3、monotonic raw clock的定义如下：

> struct k\_clock clock\_monotonic\_raw = {   
> .clock\_getres = hrtimer\_get\_res,   
> .clock\_get = posix\_get\_monotonic\_raw,   
> };

posix\_get\_monotonic\_raw函数是调用timekeeping模块getrawmonotonic接口函数实现获取monotonic raw clock当前时间数值的。和monotonic clock一样，不能设定。和monotonic clock不同的是该clock没有timer相关的callback函数。

4、coarse clock

> struct k\_clock clock\_realtime\_coarse = {   
> .clock\_getres = posix\_get\_coarse\_res,   
> .clock\_get = posix\_get\_realtime\_coarse,   
> };   
> struct k\_clock clock\_monotonic\_coarse = {   
> .clock\_getres = posix\_get\_coarse\_res,   
> .clock\_get = posix\_get\_monotonic\_coarse,   
> };

这两个clock的精度都是和tick相关的，KTIME\_LOW\_RES定义就是tick的纳秒数值。clock\_get函数分别调用current\_kernel\_time和get\_monotonic\_coarse获取当前时间点的值。

CLOCK\_BOOTTIME和CLOCK\_TAI的clock实现非常简单，大家自行阅读代码就OK了。

四、CPU-time clock

1、概述

从用户空间的角度看，有两种CPU-time clock的应用场景：

（1）调用clock\_xxx函数并传递CLOCK\_PROCESS\_CPUTIME\_ID或者CLOCK\_THREAD\_CPUTIME\_ID给该函数

（2）调用clock\_getcpuclockid或者pthread\_getcpuclockid函数来获取指定进程或者线程的clock id，之后调用clock\_xxx函数并传递该clock id参数

应对第一种场景，系统初始化的时候会调用init\_posix\_cpu\_timers函数对静态定义的CPU-time clock进行注册。对于第二种场景，内核静态定义了一个clock\_posix\_cpu的clock来应对这种需求。

2、指定进程或者线程的CPU-time clock

内核静态定义了一个clock如下（去掉了timer的callback函数）：

> struct k\_clock clock\_posix\_cpu = {   
> .clock\_getres = posix\_cpu\_clock\_getres,   
> .clock\_set = posix\_cpu\_clock\_set,   
> .clock\_get = posix\_cpu\_clock\_get,   
> .nsleep = posix\_cpu\_nsleep,   
> .nsleep\_restart = posix\_cpu\_nsleep\_restart,   
> };

（1）获取精度信息

> static int posix\_cpu\_clock\_getres(const clockid\_t which\_clock, struct timespec \*tp)   
> {   
> int error = check\_clock(which\_clock);－－－－－－－－参数校验   
> if (!error) {   
> tp->tv\_sec = 0;   
> tp->tv\_nsec = ((NSEC\_PER\_SEC + HZ - 1) / HZ);   
> if (CPUCLOCK\_WHICH(which\_clock) == CPUCLOCK\_SCHED) {   
> tp->tv\_nsec = 1;   
> }   
> }   
> return error;   
> }

该函数的执行逻辑分成两个部分，一部分是参数校验，一部分是返回精度。参数校验需要检查的包括：

（a）clock id中的高29个bit包含了pid，获取pid的代码如下：

> #define CPUCLOCK\_PID(clock) ((pid\_t) ~((clock) >> 3))

从代码可知，实际上并不是将pid放到高29个bit，而是将反码保存到了高29个bit。为何保存反码？这样做为了确保clock id是一个负数（MSB是1），还记得clockid\_to\_kclock的实现吗？要获取该clock id的精度，要确保该pid的task存在

（b）如果该clock id是一个进程相关的（调用clock\_getcpuclockid获得），那么这个进程id应该是一个实实在在的进程id。在linux kernel中，pid实际上是线程ID，POSIX标准的进程ID，也就是PID在内核中被成为线程组ID。因此，所谓一个“实实在在的进程id”就是说该线程的id（pid）和tgid一样，该pid标识的线程是线程组leader。当然，就是获取精度而已，实际上要求并不要那么严格，也许该pid标识的线程leader会退出，因此实际上要求该pid标识的task有thread group leader就OK了。（这里有可能理解有误，TODO）

（c）如果该clock id是一个线程相关的（调用pthread\_getcpuclockid获得），那么调用者必须和该线程（clock id中指明的那个线程）属于一个进程（线程组）。

返回精度部分的代码逻辑很简单，对于PROF和VIRT类型的CPU-time clock，其精度是tick，对于SCHED类型，精度是1ns。

（2）获取当前时间值

同样的，首先需要从clock id中获取pid的值，然后根据pid的值获取对应的task sturct，如果pid等于0，那么不需要费劲去寻找。得到task struct之后，可以调用posix\_cpu\_clock\_get\_task函数获取时间值：

> static int posix\_cpu\_clock\_get\_task(struct task\_struct \*tsk, const clockid\_t which\_clock,   
> struct timespec \*tp)   
> {   
> int err = -EINVAL;   
> unsigned long long rtn;
>
> if (CPUCLOCK\_PERTHREAD(which\_clock)) {－－－per 线程的cpu clock   
> if (same\_thread\_group(tsk, current))－－－必须和调用者是同一个线程组，也就是同一个进程   
> err = cpu\_clock\_sample(which\_clock, tsk, &rtn);   
> } else {
>
> if (tsk == current || thread\_group\_leader(tsk))－－－进程的cpu clock   
> err = cpu\_clock\_sample\_group(which\_clock, tsk, &rtn);   
> }
>
> if (!err)   
> sample\_to\_timespec(which\_clock, rtn, tp); －－－给返回值赋值
>
> return err;   
> }

这里仍然存在校验问题，也就是说是否允许调用者获取该task的CPU-time clock。对于进程，只允许调用者进程获取自己的CPU-time clock，在多线程环境下，主线程（线程组leader）可以获取整个进程的CPU-time clock信息。对于per线程的操作，必须和调用者是同一个线程组，也就是同一个进程。

（a）获取线程的clock信息

> static int cpu\_clock\_sample(const clockid\_t which\_clock, struct task\_struct \*p,   
> unsigned long long \*sample)   
> {   
> switch (CPUCLOCK\_WHICH(which\_clock)) {   
> default:   
> return -EINVAL;   
> case CPUCLOCK\_PROF:   
> \*sample = prof\_ticks(p);－－－－获取该task在用户空间加上在kernel space的执行时间   
> break;   
> case CPUCLOCK\_VIRT:   
> \*sample = virt\_ticks(p);－－－－获取该task在用户空间的执行时间   
> break;   
> case CPUCLOCK\_SCHED:   
> \*sample = task\_sched\_runtime(p);－－－－和调度器相关的cpu clock   
> break;   
> }   
> return 0;   
> }

计算进程或者线程在cpu上的执行时间是一个挺烦人的事，一方面想要精度高，另外一方面又不想计算量大。因此，实际上CPU-time clock有三种，CPUCLOCK\_PROF和CPUCLOCK\_VIRT这两种都是比较粗略估计CPU执行时间的clock，它的工作原理就是在周期性tick中进行进程cpu time的统计，如果该tick是用户态（timer中断了用户态程序的执行），那么整个tick的时间都是该进程的用户态执行时间。如果该tick是内核态，并且是用户程序进行系统调用而陷入内核，那么整个tick的时间都是该进程的系统态执行时间。

CPUCLOCK\_SCHED clock和上面的方法不一样，它的精度是纳秒级别的，是在调度器上进行计算进程时间。具体的计算方法还是留到调度器文章中再描述吧。

（b）cpu\_clock\_sample\_group函数概念类似，不过是统计一个进程上所有线程的时间而已。

3、CLOCK\_PROCESS\_CPUTIME\_ID 类型的clock

> struct k\_clock process = {   
> .clock\_getres = process\_cpu\_clock\_getres,   
> .clock\_get = process\_cpu\_clock\_get,   
> .nsleep = process\_cpu\_nsleep,   
> .nsleep\_restart = process\_cpu\_nsleep\_restart,   
> };

process\_cpu\_clock\_getres用来获取时间精度，该函数实际是调用posix\_cpu\_clock\_getres(PROCESS\_CLOCK, tp)来完成的。process\_cpu\_clock\_get用来获取当前时间值，实际上是通过调用posix\_cpu\_clock\_get完成。posix\_cpu\_clock\_xxx函数在上一节中已经描述。

4、CLOCK\_THREAD\_CPUTIME\_ID类型的clock

很简单，大家自行学习吧。

五、动态分配clock

1、源由

某些硬件提供了计时的能力，可以实现成一个posix clock，同时，这些硬件又类似USB设备那样可以热拔插，这也就意味着该posix clock不能静态定义。此外，除了标准的timer和clock相关的操作，这些提供计时能力的硬件还需要一些其他的类似字符设备界面的控制接口，在这样的需求推动下，内核提供了dynamic posix clock。

2、dynamic posix clock

系统中的每一个dynamic posix clock用struct posix\_clock来抽象，如下：

> struct posix\_clock {   
> struct posix\_clock\_operations ops;－－－－－－－－－－－－－－（1）   
> struct cdev cdev;－－－－－－－－－－－－－－－－－－－－－－（2）   
> struct kref kref;   
> struct rw\_semaphore rwsem;   
> bool zombie;－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> void (\*release)(struct posix\_clock \*clk);－－－－－－－－－－－－－（4）   
> };

（1）ops是该dynamic posix clock的操作函数集，分成两个group，一个是timer（例如：timer\_create、timer\_delete等）以及clock操作相关（例如clock\_gettime、clock\_settime等），另外一个是普通字符设备的操作函数（例如：open、read、write等）。

（2）该dynamic posix clock对应的cdev数据结构。在struct posix\_clock\_operations中有一个owner，其实在cdev中也有一个指向moudle的owner成员，看起来似乎是重复定义了。同样的疑问也存在与kref成员，因为在cdev中有kobject成员，kobject抽象了内核最基础的对象类别，包括名字、引用计数等，因此，我觉得只要struct posix\_clock包括了cdev成员，struct posix\_clock\_operations中的owner以及struct posix\_clock中的kref应该没有存在的必要了。

（3）zombie记录了底层硬件的状态，对于hotplug的外设，有可能硬件被拔除。rwsem用来保护该状态信息

（4）当reference count等于0的时候会调用release函数释放dynamic posix clock占用的资源。

3、注册和注销

底层的有计时能力的硬件driver可以调用posix\_clock\_register和posix\_clock\_unregister来注册或者注销一个posix clock，注册代码如下：

> int posix\_clock\_register(struct posix\_clock \*clk, dev\_t devid)   
> {   
> int err;
>
> kref\_init(&clk->kref);   
> init\_rwsem(&clk->rwsem);
>
> cdev\_init(&clk->cdev, &posix\_clock\_file\_operations);－－－－－VFS接口的操作函数集合   
> clk->cdev.owner = clk->ops.owner;   
> err = cdev\_add(&clk->cdev, devid, 1);
>
> return err;   
> }

VFS接口的操作函数集合都非常简单，基本上都是struct posix\_clock\_operations上的字符设备操作函数集合上。这样，用户空间的程序可以通过标准的文件描述符进行设备操作。

4、clock和timer接口

通过clock\_xxx或者timer\_xxx函数可以指定clock id，对于dynamic posix clock可以通过下面的操作来生成一个dynamic posix clock ID：

> #define FD\_TO\_CLOCKID(fd) ((~(clockid\_t) (fd) << 3) | CLOCKFD)

其中fd是通过设备节点打开的那个有计时能力的硬件。在内核态会通过clockid\_to\_kclock操作将clock id转换成

> static struct k\_clock \*clockid\_to\_kclock(const clockid\_t id)   
> {   
> if (id < 0)   
> return (id & CLOCKFD\_MASK) == CLOCKFD ?   
> &clock\_posix\_dynamic : &clock\_posix\_cpu;
>
> ……   
> }

clock\_posix\_dynamic可以将dynamic posix clock ID转换成对应的posix\_clock，然后调用struct posix\_clock\_operations上的time和clock相关的函数即可。

*原创文章，转发请注明出处。蜗窝科技*

/timer_subsystem/posix-clock.html
