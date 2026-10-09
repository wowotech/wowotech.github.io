---
title: "Linux时间子系统之（四）：timekeeping"
date: 2014-12-29T18:03:35+08:00
url: "/timer_subsystem/timekeeping.html"
gid: "132"
emlog_type: "blog"
summary: "timekeeping模块是一个提供时间服务的基础模块。Linux内核提供各种time line，real time clock，monotonic clock、monotonic raw clock等，timekeeping模块就是负责跟踪、维护这些timeline的，并且向其他模块（timer相关模块、用户空间的时间服务等）提供 服务，而timekeeping模块维护timeline的基础是基"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["Linux时间子系统", "timekeeping"]
views: 53918
comment_count: 16
aliases:
  - "/timer_subsystem/132.html"
  - "/132.html"
---

一、前言

timekeeping模块是一个提供时间服务的基础模块。Linux内核提供各种time line，real time clock，monotonic clock、monotonic raw clock等，timekeeping模块就是负责跟踪、维护这些timeline的，并且向其他模块（timer相关模块、用户空间的时间服务等）提供服务，而timekeeping模块维护timeline的基础是基于clocksource模块和tick模块。通过tick模块的tick事件，可以周期性的更新time line，通过clocksource模块、可以获取tick之间更精准的时间信息。

本文熟悉介绍timekeeping的一些基础概念，接着会介绍该模块初始化的过程，此后会从上至下介绍该模块提供的服务、该模块如何和tick模块交互以及如何和clocksource模块交互，最后介绍电源管理相关的内容。

二、timekeeper核心数据定义

1、struct timekeeper数据结构解析

旧的内核定义了很多零散的全局变量来管理linux kernel中的各种系统clock，现在，内核定义的struct timekeeper数据结构来管理各种系统时钟的跟踪以及控制，定义如下：

> struct timekeeper {   
> struct clocksource \*clock;－－－－－－－－－－－－－－－－－－－－－－－－（1）   
>   
> u32 mult;－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> u32 shift;
>
> cycle\_t cycle\_interval; －－－－－－－－－－－－－－－－－－－－－－－（3）   
> cycle\_t cycle\_last;   
> u64 xtime\_interval;   
> s64 xtime\_remainder;   
> u32 raw\_interval;
>
> s64 ntp\_error;   
> u32 ntp\_error\_shift;
>
> u64 xtime\_sec;－－－－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> u64 xtime\_nsec;
>
> struct timespec wall\_to\_monotonic; －－－－－－－－－－－－－－－－－－－（5）   
> ktime\_t offs\_real;   
> struct timespec total\_sleep\_time; －－－－－－记录系统睡眠时间   
> ktime\_t offs\_boot; －－－－－－－－－－－－记录系统boot time   
>   
> struct timespec raw\_time; －－－－－－－－－－－－－－－－－－－－－－－（6）   
>   
> s32 tai\_offset; －－－－－－－－－－－－－－－－－－－－－－－－－－－（7）   
> ktime\_t offs\_tai;
>
> };

（1）timekeeper当前使用的clocksource。这个clock应该系统中最优的那个，如果有好过当前clocksource注册入系统，那么clocksource模块会通知timekeeping模块来切换clocksource。

（2）clock source的cycle值和纳秒转换的facotr，概念和clocksource的mult和shift一致。

（3）NTP相关的成员，这里不详述了，实在是对NTP没有兴趣。

（4）CLOCK\_REALTIME类型的系统时钟（其实就是墙上时钟）。我们都知道，时间就像是一条直线（line），不知道起点，也不知道终点，因此我们称之time line。time line有很多种，和如何定义0值的时间以及用什么样的刻度来度量时间相关。人类熟悉的墙上时间和linux kernel中定义的CLOCK\_REALTIME都是用来描述time line的，只不过时间原点和如何度量time line上两点距离的刻度不一样。对于人类的时间，0值是耶稣诞生的时间点；对于CLOCK\_REALTIME，0值是linux epoch，即1970年1月1日...。对于墙上时间，在度量的时候虽然也是基于秒的，但是人类做了grouping，因此使用了年月日时分秒的概念。这里的秒数是相对与当前分钟值内的秒数。对于linux世界中的CLOCK\_REALTIME time，直接使用秒以及纳秒在当前秒内的偏移来表示。  
因此，这里xtime\_sec用秒这个的刻度单位来度量CLOCK\_REALTIME time line上，时间原点到当前点的距离值。当然xtime\_sec是一个对current time point的取整值，为了更好的精度，还需要一个纳秒表示的offset，也就是xtime\_nsec。  
不过为了内核内部计算精度（内核对时间的计算是基于cycle的），并不是保存了时间的纳秒偏移值，而是保存了一个shift之后的值，因此，用户看来，当前时间点的值应该是距离时间原点xtime\_sec + (xtime\_nsec << shift)距离的那个时间点值

（5）CLOCK\_MONOTONIC类型的系统时钟。这种系统时钟并没有象墙上时钟一样定义一个相对于linux epoch的值，这个成员定义了monotonic clock到real time clock的偏移，也就是说，这里的wall\_to\_monotonic和offs\_real需要加上real time clock的时间值才能得到monotonic clock的时间值。当然，从这里成员的名字就看出来了。wall\_to\_monotonic和offs\_real的意思是一样的，不过时间的格式不一样，用在不同的场合，以便获取性能的提升。

（6）CLOCK\_MONOTONIC\_RAW类型的系统时钟

（7）CLOCK\_TAI类型的系统时钟。TAI（international atomic time）是原子钟，在[时间的基本概念](/timer_subsystem/time_concept.html)文档中，我们说过，UTC就是base TAI的，也就是说用铯133的振荡频率来定义秒的那个时钟，当然UTC还有考虑leap second以便方便广大人民群众。CLOCK\_TAI类型的系统时钟就是完完全全使用铯133的振荡频率来定义秒的那个时钟，不向人类妥协。

2、全局变量

> static struct timekeeper timekeeper;   
> static DEFINE\_RAW\_SPINLOCK(timekeeper\_lock);   
> static seqcount\_t timekeeper\_seq;
>
> static struct timekeeper shadow\_timekeeper;

timekeeper维护了系统的所有的clock。一个全局变量（共享资源）没有锁保护怎么行，timekeeper\_lock和timekeeper\_seq都是用来保护timekeeper的，用在不同的场合。

shadow\_timekeeper主要用在更新系统时间的过程中。在update\_wall\_time中，首先将时间调整值设定到shadow\_timekeeper中，然后一次性的copy到真正的那个timekeeper中。这样的设计主要是可以减少持有timekeeper\_seq锁的时间（在更新系统时间的过程中），不过需要注意的是：在其他的过程中（非update\_wall\_time），需要sync shadow timekeeper。

三、timekeeping初始化

timekeeping初始化的代码位于timekeeping\_init函数中，在系统初始化的时候（start\_kernel）会调用该函数进行timekeeping的初始化。

1、从persistent clock获取当前的时间值

timekeeping模块中支持若干种system clock，这些system clock的数据保存在ram中，一旦断电，数据就丢失了。因此，在系加电启动后，会从persistent clock中中取出当前时间值（例如RTC，RTC有battery供电，因此系统断电也可以保存数据），根据情况初始化各种system clock。具体代码如下：

> read\_persistent\_clock(&now);－－－－－－－－－－－－－－－－－－－－－－（1）   
> if (!timespec\_valid\_strict(&now)) {－－－－－－－－－－－－－－－－－－－－－（2）   
> now.tv\_sec = 0;   
> now.tv\_nsec = 0;   
> } else if (now.tv\_sec || now.tv\_nsec)   
> persistent\_clock\_exist = true; －－－－－－－－－－－－－－－－－－－－－（3）
>
> read\_boot\_clock(&boot);－－－－－－－－－－－概念同上   
> if (!timespec\_valid\_strict(&boot)) {   
> boot.tv\_sec = 0;   
> boot.tv\_nsec = 0;   
> }

（1）read\_persistent\_clock是一个和architecture相关的函数，具体如何支持可以看具体的architecture相关的代码实现。对于ARM，其实现在linux/arch/arm/kernel/time.c文件中。该函数的功能就是从系统中的HW clock（例如RTC）中获取时间信息。

（2）timespec\_valid\_strict用来校验一个timespec是否是有效。如何判断从RTC获取的值是有效的呢？要满足timespec中的秒数值要大于等于0，小于KTIME\_SEC\_MAX，纳秒值要小于NSEC\_PER\_SEC（10^9）。KTIME\_SEC\_MAX这个宏定义了ktime\_t这种类型的数据可以表示的最大的秒数值，从RTC中读出的秒数值当然不能大于它，KTIME\_SEC\_MAX定义如下：

> #define KTIME\_MAX ((s64)~((u64)1 << 63))   
> #if (BITS\_PER\_LONG == 64)   
> # define KTIME\_SEC\_MAX (KTIME\_MAX / NSEC\_PER\_SEC)   
> #else   
> # define KTIME\_SEC\_MAX LONG\_MAX   
> #endif

ktime\_t这种数据类型占据了64 bit的size，对于64 bit的CPU和32 bit CPU上是不一样的，64 bit的CPU上定义为一个signed long long，该值直接表示了纳秒值。对于32bit CPU而言，64 bit的数据分成两个signed int类型，分别表示秒数和纳秒数。

（3）设定persistent\_clock\_exist flag，说明系统中存在RTC的硬件模块，timekeeping模块会和RTC模块进行交互。例如：在suspend的时候，如果该flag是true的话，RTC driver不能sleep，因为timekeeping模块还需要在resume的时候通过RTC的值恢复其时间值呢。

2、为timekeeping模块设置default的clock source

> clock = clocksource\_default\_clock();－－－－－－－－－－－－－－－－－－－－（1）   
> if (clock->enable)   
> clock->enable(clock);－－－－－enalbe default clocksource   
> tk\_setup\_internals(tk, clock);－－－－－－－－－－－－－－－－－－－－－－－－（2）

（1）在timekeeping初始化的时候，很难选择一个最好的clock source，因为很有可能最好的那个还没有初始化呢。因此，这里的策略就是采用一个在timekeeping初始化时一定是ready的clock source，也就是基于jiffies 的那个clocksource。clocksource\_default\_clock定义在kernel/time/jiffies.c，是一个weak symble，如果你愿意也可以重新定义clocksource\_default\_clock这个函数。不过，要保证在timekeeping初始化的时候是ready的。

（2）建立default clocksource和timekeeping伙伴关系。

3、初始化real time clock、monotonic clock和monotonic raw clock

> tk\_set\_xtime(tk, &now);－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> tk->raw\_time.tv\_sec = 0;－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> tk->raw\_time.tv\_nsec = 0;   
> if (boot.tv\_sec == 0 && boot.tv\_nsec == 0)   
> boot = tk\_xtime(tk); －－－如果没有获取到有效的booting time，那么就选择当前的real time clock
>
> set\_normalized\_timespec(&tmp, -boot.tv\_sec, -boot.tv\_nsec);－－－－－－－－－－（3）   
> tk\_set\_wall\_to\_mono(tk, tmp);
>
> tmp.tv\_sec = 0;   
> tmp.tv\_nsec = 0;   
> tk\_set\_sleep\_time(tk, tmp);－－－－－－初始化sleep time为0

（1）根据从RTC中获取的时间值来初始化timekeeping中的real time clock，如果没有获取到正确的RTC时间值，那么缺省的real time（wall time）就是linux epoch。

（2）monotonic raw clock被设定为从0开始。

（3）启动时将monotonic clock设定为负的real time clock，timekeeper并没有直接保存monotonic clock，而是保存了一个wall\_to\_monotonic的值，这个值类似offset，real time clock加上这个offset就可以得到monotonic clock。因此，初始化的时间点上，monotonic clock实际上等于0（如果没有获取到有效的booting time）。当系统运行之后，real time clock+ wall\_to\_monotonic是系统的uptime，而real time clock+ wall\_to\_monotonic + sleep time也就是系统的boot time。

四、获取和设定当前系统时钟的时间值

1、获取monotonic clock的时间值：ktime\_get和ktime\_get\_ts

> ktime\_t ktime\_get(void)   
> {   
> struct timekeeper \*tk = &timekeeper;   
> unsigned int seq;   
> s64 secs, nsecs;
>
> do {   
> seq = read\_seqcount\_begin(&timekeeper\_seq);   
> secs = tk->xtime\_sec + tk->wall\_to\_monotonic.tv\_sec;－－－－－获取monotonic clock的秒值   
> nsecs = timekeeping\_get\_ns(tk) + tk->wall\_to\_monotonic.tv\_nsec; －－－获取纳秒值
>
> } while (read\_seqcount\_retry(&timekeeper\_seq, seq));   
>   
> return ktime\_add\_ns(ktime\_set(secs, 0), nsecs);－－－－返回一个ktime类型的时间值   
> }

一般而言，timekeeping模块是在tick到来的时候更新各种系统时钟的时间值，ktime\_get调用很有可能发生在两次tick之间，这时候，仅仅依靠当前系统时钟的值精度就不甚理想了，毕竟那个时间值是per tick更新的。因此，为了获得高精度，ns值的获取是通过timekeeping\_get\_ns完成的，该函数获取了real time clock的当前时刻的纳秒值，而这是通过上一次的tick时候的real time clock的时间值（xtime\_nsec）加上当前时刻到上一次tick之间的delta时间值计算得到的。

ktime\_get\_ts的概念和ktime\_get是一样的，只不过返回的时间值格式不一样而已。

2、获取real time clock的时间值：ktime\_get\_real和ktime\_get\_real\_ts

这两个函数的具体逻辑动作和获取monotonic clock的时间值函数是完全一样的，大家可以自己看代码分析。这里稍微提一下另外一个函数：current\_kernel\_time，代码如下：

> static inline struct timespec tk\_xtime(struct timekeeper \*tk)   
> {   
> struct timespec ts;
>
> ts.tv\_sec = tk->xtime\_sec;   
> ts.tv\_nsec = (long)(tk->xtime\_nsec >> tk->shift);   
> return ts;   
> }
>
> struct timespec current\_kernel\_time(void)   
> {   
> struct timekeeper \*tk = &timekeeper;   
> struct timespec now;   
> unsigned long seq;
>
> do {   
> seq = read\_seqcount\_begin(&timekeeper\_seq);
>
> now = tk\_xtime(tk);   
> } while (read\_seqcount\_retry(&timekeeper\_seq, seq));
>
> return now;   
> }

上面的代码并没有调用clocksource的read函数获取tick之间的delta时间值，因此current\_kernel\_time是一个粗略版本的real time clock，精度低于ktime\_get\_real，不过性能要好些。类似的，monotonic clock也有一个get\_monotonic\_coarse函数，概念类似current\_kernel\_time。

3、获取boot clock的时间值：ktime\_get\_boottime和get\_monotonic\_boottime

> ktime\_t ktime\_get\_boottime(void)   
> {   
> struct timespec ts;
>
> get\_monotonic\_boottime(&ts);   
> return timespec\_to\_ktime(ts);   
> }

boot clock这个系统时钟和monotonic clock有什么不同？monotonic clock是从一个固定点开始作为epoch，对于linux，就是启动的时间点，因此，monotonic clock是一个从0开始增加的clock，并且不接受用户的setting，看起来好象适合boot clock是一致的，不过它们之间唯一的差别是对系统进入suspend的处理，对于monotonic clock，它是不记录系统睡眠时间的，因此monotonic clock得到的是一个system uptime。而boot clock计算睡眠时间，直到系统reboot。

ktime\_get\_boottime返回ktime的时间值，get\_monotonic\_boottime函数返回timespec格式的时间值。

4、获取TAI clock的时间值：ktime\_get\_clocktai和timekeeping\_clocktai

原子钟和real time clock（UTC）是类似的，只是有一个偏移而已，记录在tai\_offset中。代码非常简单，大家自己阅读即可。ktime\_get\_clocktai返回ktime的时间值，而timekeeping\_clocktai返回timespec格式的时间值。

5、设定wall time clock

> int do\_settimeofday(const struct timespec \*tv)   
> {
>
> ……
>
> timekeeping\_forward\_now(tk);－－－更新timekeeper至当前时间
>
> xt = tk\_xtime(tk);   
> ts\_delta.tv\_sec = tv->tv\_sec - xt.tv\_sec;   
> ts\_delta.tv\_nsec = tv->tv\_nsec - xt.tv\_nsec; －－－－计算delta
>
> tk\_set\_wall\_to\_mono(tk, timespec\_sub(tk->wall\_to\_monotonic, ts\_delta)); －－不调mono clock
>
> tk\_set\_xtime(tk, tv); －－－调整wall time clock
>
> timekeeping\_update(tk, TK\_CLEAR\_NTP | TK\_MIRROR | TK\_CLOCK\_WAS\_SET); －－更tk
>
> ……   
> }

五、和clocksource模块的交互

除了直接调用clocksource的read函数之外，timekeeping和clocksource主要的交互就是change clocksource的操作了。当系统中有更高精度的clocksource的时候，会调用timekeeping\_notify函数通知timekeeping模块进行clock source的切换，代码如下：

> int timekeeping\_notify(struct clocksource \*clock)   
> {   
> struct timekeeper \*tk = &timekeeper;
>
> if (tk->clock == clock)－－－－新的clocksource和旧的一样，不需要切换   
> return 0;   
> stop\_machine(change\_clocksource, clock, NULL);   
> tick\_clock\_notify();－－－－通知tick模块，具体在其他文档中描述   
> return tk->clock == clock ? 0 : -1;   
> }

stop\_machine从字面上就可以知道是停掉了所有cpu上的任务（这个machine都不能对外提供服务了），只是执行一个函数，在这个场景下是change\_clocksource。（为何不直接调用change\_clocksource而是使用stop\_machine这样的大招？现在还在思考中……）。change\_clocksource主要执行的步骤包括：

（1）调用timekeeping\_forward\_now函数。就要更换新的clocksource了，就是旧clocksource最后再发挥一次作用。调用旧的clocksource的read函数，将最后的这段时间间隔（当前到上次read）加到real time system clock以及minitonic raw system clock上去。

（2）调用tk\_setup\_internals函数设定新的clocksource，disable旧的clocksource。tk\_setup\_internals函数代码如下：

> static void tk\_setup\_internals(struct timekeeper \*tk, struct clocksource \*clock)   
> {   
> cycle\_t interval;   
> u64 tmp, ntpinterval;   
> struct clocksource \*old\_clock;
>
> old\_clock = tk->clock;   
> tk->clock = clock;－－－更换为新的clocksource   
> tk->cycle\_last = clock->cycle\_last = clock->read(clock); －－－－更新last cycle值
>
> tmp = NTP\_INTERVAL\_LENGTH;－－－NTP interval设定的纳秒数   
> tmp <<= clock->shift;   
> ntpinterval = tmp;－－－－计算remainder的时候会用到   
> tmp += clock->mult/2;   
> do\_div(tmp, clock->mult);－－－－－－将NTP interval的纳秒值转成新clocksource的cycle值   
> if (tmp == 0)   
> tmp = 1;
>
> interval = (cycle\_t) tmp;   
> tk->cycle\_interval = interval; －－－设定新的NTP interval的cycle值
>
> tk->xtime\_interval = (u64) interval \* clock->mult;－－－－将NTP interval的cycle值转成ns   
> tk->xtime\_remainder = ntpinterval - tk->xtime\_interval;－－－计算remainder   
> tk->raw\_interval =   
> ((u64) interval \* clock->mult) >> clock->shift; －－－－－NTP interval的ns值
>
> if (old\_clock) {－－－－－－xtime\_nsec保存的是不是实际的ns值而是一个没有执行shift版本的   
> int shift\_change = clock->shift - old\_clock->shift;   
> if (shift\_change < 0)－－－－－如果新旧的shift值不一样，那么当前的xtime\_nsec要修正   
> tk->xtime\_nsec >>= -shift\_change;   
> else   
> tk->xtime\_nsec <<= shift\_change;   
> }   
> tk->shift = clock->shift; －－－－－更换新的shift factor
>
> tk->ntp\_error = 0;   
> tk->ntp\_error\_shift = NTP\_SCALE\_SHIFT - clock->shift;
>
> tk->mult = clock->mult;－－－－－更换新的mult factor   
> }

由于更换了新的clocksource，一般而言，新旧clocksource的工作参数不一样，就要就导致timekeeper的一些内部的数据成员要进行更新，例如NTP interval、multi和shift facotr数值等。

（3）调用timekeeping\_update函数。由于更新了clocksource，因此timekeeping模块要更新其内部数据。TK\_CLEAR\_NTP控制clear 旧的NTP的状态数据。TK\_MIRROR用来更新shadow timekeeper，主要是为了保持和real timekeeper同步。TK\_CLOCK\_WAS\_SET用在paravirtual clock场景中，这里就不详细描述了。

六、和tick device模块的接口

1、periodic tick

当系统采用periodic tick机制的时候，tick device模块会在周期性tick到来的时候，调用tick\_periodic来进行下面的动作：

（1）如果是global tick，需要调用do\_timer来修改jiffies，计算系统负荷。

（2）如果是global tick，需要调用update\_wall\_time来更新系统时间。timekeeping模块是按照自己的节奏来更新系统时间的，更新一般是发生在周期性tick到来的时候。如果HZ＝100的话，那么每10ms就会有一个tick事件（clockevent事件），跟的太紧，会浪费CPU，跟的太松会损失一些精度。timekeeper中的cycle\_interval成员就是周期性tick的cycle interval，如果距离上次的更新还不到一个tick的时间，那么就不再更新系统时间，直接退出。

（3）调用update\_process\_times和profile\_tick，分别更新进程时间和进行内核剖析相关的操作。

2、dynamic tick

TODO

七、timekeeping模的电源管理

1、初始化

> static struct syscore\_ops timekeeping\_syscore\_ops = {   
> .resume = timekeeping\_resume,   
> .suspend = timekeeping\_suspend,   
> };
>
> static int \_\_init timekeeping\_init\_ops(void)   
> {   
> register\_syscore\_ops(&timekeeping\_syscore\_ops);   
> return 0;   
> }
>
> device\_initcall(timekeeping\_init\_ops);

在系统初始化的过程中，会调用 timekeeping\_init\_ops来注册和timekeeping相关的system core operations。在旧的内核中，这部分的功能是通过sysdev class和sysdev实现的。通过sysdev class和sysdev实现的suspend和resume看起来比较笨重而且效率低，因此新的内核为某些core subsystem设计了新的基于syscore\_ops 的接口。而注册的这些callback函数会在系统suspend和resume的时候，在适当的时机执行（在system suspend过程中，syscore suspend的执行非常的靠后，在那些普通的总线设备之后，对应的，system resume过程中，非常早的醒来进入工作状态）。当然，这属于电源管理子系统的内容，这篇文章就不描述了，大家可以参考suspend\_enter函数。

2、suspned 回调函数

> static int timekeeping\_suspend(void)   
> {   
> struct timekeeper \*tk = &timekeeper;   
> unsigned long flags;   
> struct timespec delta, delta\_delta;   
> static struct timespec old\_delta;
>
> read\_persistent\_clock(&timekeeping\_suspend\_time); －－－－－－－－－－－－（1）   
> if (timekeeping\_suspend\_time.tv\_sec || timekeeping\_suspend\_time.tv\_nsec)   
> persistent\_clock\_exist = true;
>
> raw\_spin\_lock\_irqsave(&timekeeper\_lock, flags);   
> write\_seqcount\_begin(&timekeeper\_seq);   
> timekeeping\_forward\_now(tk);－－－－－－－－－－－－－－－－－－－－－－（2）   
> timekeeping\_suspended = 1; －－－－－－－－－－－－－－－－－－－－－－（3）
>
> delta = timespec\_sub(tk\_xtime(tk), timekeeping\_suspend\_time);－－－－－－－（4）   
> delta\_delta = timespec\_sub(delta, old\_delta);   
> if (abs(delta\_delta.tv\_sec) >= 2) {   
> old\_delta = delta;   
> } else {   
> timekeeping\_suspend\_time =   
> timespec\_add(timekeeping\_suspend\_time, delta\_delta);   
> }
>
> timekeeping\_update(tk, TK\_MIRROR);－－－－更新shadow timekeeper   
> write\_seqcount\_end(&timekeeper\_seq);   
> raw\_spin\_unlock\_irqrestore(&timekeeper\_lock, flags);
>
> clockevents\_notify(CLOCK\_EVT\_NOTIFY\_SUSPEND, NULL);－－－－－－－－（5）   
> clocksource\_suspend();－－－suspend系统中所有的clocksource设备   
> clockevents\_suspend(); －－－suspend系统中所有的clockevent设备
>
> return 0;   
> }

（1）一般而言，在整机suspend之后，clocksource和clockevent所依赖的底层硬件会被推入深度睡眠甚至是断电状态（当然，也有一些例外，有些clocksource会标记CLOCK\_SOURCE\_SUSPEND\_NONSTOP flag），这时候，有些有计时能力的硬件（persistent clock），例如RTC，仍然是running状态。虽然RTC的精度不是很好，但是time keeping的动作在suspend中的时候也要继续，需要记录这一段时间的流逝。因此，这里调用read\_persistent\_clock将suspend时间点信息记录到timekeeping\_suspend\_time变量中。persistent\_clock\_exist变量标识系统中是否有RTC的硬件，按理说应该在timekeeping初始化的时候设定，不过也有可能在那个时刻，系统中RTC驱动还没有初始化，因此，如果这里能得到一个有效的时间值的话，也相应的更新persistent\_clock\_exist变量。

（2）timekeeping subsystem马上就睡下去了，临睡前，最后一次更新timekeeper的系统时钟的数据，此后，底层的硬件会停掉，硬件counter和硬件timer都会停止工作了。

（3）标记timekeeping subsystem进入suspend过程。在这个过程中的获取时间操作应该被禁止。

（4）persistent clock的精度一般没有那么好，可能只是以秒的精度在计时。因此，一次suspend/resume的过程中，read persistent clock会引入半秒的误差。为了防止连续的suspend/resume引起时间偏移，这里也考虑了real time clock和persistent clock之间的delta值。delta是本次real time clock和persistent clock之间的差值，delta\_delta是两次suspend之间delta的差值，如果delta\_delta大于2秒，

（5）调用clockevents\_notify函数通知clockevent模块系统suspend事件。

3、resume回调函数

> static void timekeeping\_resume(void)   
> {   
> struct timekeeper \*tk = &timekeeper;   
> struct clocksource \*clock = tk->clock;   
> unsigned long flags;   
> struct timespec ts\_new, ts\_delta;   
> cycle\_t cycle\_now, cycle\_delta;   
> bool suspendtime\_found = false;
>
> read\_persistent\_clock(&ts\_new); －－－－－－通过persistent clock记录醒来的时间点
>
> clockevents\_resume();－－－－－－－－－－－resume系统中所有的clockevent设备   
> clocksource\_resume(); －－－－－－－－－－resume系统中所有的clocksource设备
>
> cycle\_now = clock->read(clock);   
> if ((clock->flags & CLOCK\_SOURCE\_SUSPEND\_NONSTOP) &&   
> cycle\_now > clock->cycle\_last) {－－－－－－－－－－－－－－－－－－－－－－（1）   
> u64 num, max = ULLONG\_MAX;   
> u32 mult = clock->mult;   
> u32 shift = clock->shift;   
> s64 nsec = 0;
>
> cycle\_delta = (cycle\_now - clock->cycle\_last) & clock->mask; －－－本次suspend的时间   
> do\_div(max, mult);   
> if (cycle\_delta > max) {   
> num = div64\_u64(cycle\_delta, max);   
> nsec = (((u64) max \* mult) >> shift) \* num;   
> cycle\_delta -= num \* max;   
> }   
> nsec += ((u64) cycle\_delta \* mult) >> shift; －－－－将suspend时间从cycle转换成ns
>
> ts\_delta = ns\_to\_timespec(nsec);－－－－将suspend时间从ns转换成timespec   
> suspendtime\_found = true;   
> } else if (timespec\_compare(&ts\_new, &timekeeping\_suspend\_time) > 0) {－－－－－（2）   
> ts\_delta = timespec\_sub(ts\_new, timekeeping\_suspend\_time);   
> suspendtime\_found = true;   
> }
>
> if (suspendtime\_found)   
> \_\_timekeeping\_inject\_sleeptime(tk, &ts\_delta); －－－－－－－－－－－－－－－－（3）
>
> tk->cycle\_last = clock->cycle\_last = cycle\_now; －－－更新last cycle的值   
> tk->ntp\_error = 0;   
> timekeeping\_suspended = 0; －－－－标记完成了suspend/resume过程   
> timekeeping\_update(tk, TK\_MIRROR | TK\_CLOCK\_WAS\_SET); －－更新shadow timerkeeper   
> write\_seqcount\_end(&timekeeper\_seq);   
> raw\_spin\_unlock\_irqrestore(&timekeeper\_lock, flags);
>
> touch\_softlockup\_watchdog();
>
> clockevents\_notify(CLOCK\_EVT\_NOTIFY\_RESUME, NULL); －－－通知resume信息到clockevent   
> hrtimers\_resume(); －－－高精度timer相关，另文描述   
> }

（1）如果timekeeper当前的clocksource在suspend的时候没有stop，那么有机会使用精度更高的clocksource而不是persistent clock。前提是clocksource没有溢出，因此才有了cycle\_now > clock->cycle\_last的判断（不过，这里要求clocksource应该有一个很长的overflow的时间）。

（2）如果没有suspend nonstop的clock，也没有关系，可以用persistent clock的时间值。

（3）调用\_\_timekeeping\_inject\_sleeptime函数，具体如下：

> static void \_\_timekeeping\_inject\_sleeptime(struct timekeeper \*tk, struct timespec \*delta)   
> {   
> tk\_xtime\_add(tk, delta);－－－－－－将suspend的时间加到real time clock上去   
> tk\_set\_wall\_to\_mono(tk, timespec\_sub(tk->wall\_to\_monotonic, \*delta));   
> tk\_set\_sleep\_time(tk, timespec\_add(tk->total\_sleep\_time, \*delta));   
> tk\_debug\_account\_sleep\_time(delta);   
> }

monotonic clock不计sleep时间，因此wall\_to\_monotonic要减去suspend的时间值。total\_sleep\_time当然需要加上suspend的时间值。

*原创文章，转发请注明出处。蜗窝科技*

[/timer_subsystem/timekeeping.html](/timer_subsystem/timekeeping.html)
