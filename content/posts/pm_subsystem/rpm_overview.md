---
title: "Linux电源管理(11)_Runtime PM之功能描述"
date: 2014-10-08T23:32:12+08:00
url: "/pm_subsystem/rpm_overview.html"
gid: "94"
emlog_type: "blog"
summary: "终于可以写Runtime PM了，说实话，蜗蜗有点小激动。因为从个人的角度讲，我很推崇使用Runtime PM进行日常的动态电源管理，而不是suspend机制。 软件工程的基本思想就是模块化：高内聚和低耦合。通俗地讲呢，就是“各人自扫门前雪”，尽量扫好自己的（高内聚），尽量不和别人交互（低耦合）。而Runtime PM正体现了这一思想：每个设备（包括CPU）都处理好自身的电源管理工作，尽量以最低的"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "runtime", "rpm"]
views: 92813
comment_count: 56
aliases:
  - "/pm_subsystem/94.html"
  - "/94.html"
---

#### 1. 前言

终于可以写Runtime PM（后面简称RPM）了，说实话，蜗蜗有点小激动。因为从个人的角度讲，我很推崇使用RPM进行日常的动态电源管理，而不是suspend机制。

软件工程的基本思想就是模块化：高内聚和低耦合。通俗地讲呢，就是“各人自扫门前雪”，尽量扫好自己的（高内聚），尽量不和别人交互（低耦合）。而RPM正体现了这一思想：每个设备（包括CPU）都处理好自身的电源管理工作，尽量以最低的能耗完成交代的任务，尽量在不需要工作的时候进入低功耗状态，尽量不和其它模块有过多耦合。每个设备都是最节省的话，整个系统一定是最节省的，最终达到无所谓睡、无所谓醒的天人合一状态。

讲到这里想到自己的一则趣事：大学时，蜗蜗是寝室长，但不爱打扫卫生，于是就提出一个口号，“不污染，不治理；谁污染，谁治理”。结果呢，大家猜就是了，呵呵。言归正传，开始吧。

#### 2. Runtime PM的软件框架

听多了RPM的传说，有种莫名的恐惧，觉的会很复杂。但看代码，也就是“drivers/base/power/runtime.c”中1400行而已。

从设计思路上讲，它确实简单。下面是一个大概的软件框架：

[![Runtime PM architecture](/content/uploadfile/201410/4f0b5b3e8e1dcfd7ce36e34e69fc909720141009152818.gif "Runtime PM architecture")](/content/uploadfile/201410/f03735c6ab3d2842f47a4b3afca7d37e20141009152816.gif)

device driver（或者driver所在的bus、class等）需要提供3个回调函数，runtime\_suspend、runtime\_resume和runtime\_idle，分别用于suspend device、resume device和idle device。它们一般由RPM core在合适的时机调用，以便降低device的power consumption。

而调用的时机，最终是由device driver决定的。driver会在适当的操作点，调用RPM core提供的put和get系列的helper function，汇报device的当前状态。RPM core会为每个device维护一个引用计数，get时增加计数值，put时减少计数值，当计数为0时，表明device不再被使用，可以立即或一段时间后suspend，以节省功耗。

好吧，说总是简单，那做呢？很不幸，到目前为止，linux kernel的runtime PM还是很复杂。这里的复杂，不是从实现的角度，而是从对外的角度。在“include\linux\pm\_runtime.h”中，RPM提供了将近50个接口。软件模块化的设计理念中，最重要的一个原则就是提供简洁的接口。很显然，RPM没有做到！

无论RPM面对的问题有多么复杂，无论理由有多么充分，它也应坚守“简洁性”这一原则。否则，结果只有一个----无人敢用。这就是当前Linux kernel电源管理中“[Opportunistic suspend](/pm_subsystem/autosleep.html)”和RPM两种机制并存的原因。但是，就算现状不理想，也不能否认RPM的先进性，在当前以及未来很长的一段时间内，它会是kernel电源管理更新比较活跃的部分，因为可以做的还很多。

鉴于这个现状，本文以及后续RPM有关的文章，会选取最新的kernel（当前为[linux-3.17](https://kernel.org/pub/linux/kernel/v3.x/linux-3.17.tar.xz "linux-3.17")），以便及时同步相关的更新。

#### 3. Runtime PM的运行机制

##### 3.1 核心机制

RPM的核心机制是这样的：

1）为每个设备维护一个引用计数（device->power.usage\_count），用于指示该设备的使用状态。

2）需要使用设备时，device driver调用pm\_runtime\_get（或pm\_runtime\_get\_sync）接口，增加引用计数；不再使用设备时，device driver调用pm\_runtime\_put（或pm\_runtime\_put\_sync）接口，减少引用计数。

3）每一次put，RPM core都会判断引用计数的值。如果为零，表示该设备不再使用（idle）了，则使用异步（ASYNC）或同步（SYNC）的方式，调用设备的.runtime\_idle回调函数。

4）.runtime\_idle的存在，是为了在idle和suspend之间加一个缓冲，避免频繁的suspend/resume操作。因此它的职责是：判断设备是否具备suspend的条件，如果具备，在合适的时机，suspend设备。

> 可以不提供，RPM core会使用异步（ASYNC）或同步（SYNC）的方式，调用设备的.runtime\_suspend回调函数，suspend设备，同时记录设备的PM状态；
>
> 可以调用RPM core提供helper函数（pm\_runtime\_autosuspend\_expiration、pm\_runtime\_autosuspend、pm\_request\_autosuspend），要求在指定的时间后，suspend设备。

5）pm\_runtime\_autosuspend、pm\_request\_autosuspend等接口，会起一个timer，并在timer到期后，使用异步（ASYNC）或同步（SYNC）的方式，调用设备的.runtime\_suspend回调函数，suspend设备，同时记录设备的PM状态。

6）每一次get，RPM core都会判断设备的PM状态，如果不是active，则会使用异步（ASYNC）或同步（SYNC）的方式，调用设备的.runtime\_resume回调函数，resume设备。

注1：Runtime PM中的“suspend”，不一定要求设备必须进入低功耗状态，而是要求设备在suspend后，不再处理数据，不再和CPUs、RAM进行任何的交互，直到设备的.runtime\_resume被调用。因为此时设备的parent（如bus controller）、CPU是、RAM等，都有可能因为suspend而不再工作，如果设备再有任何动作，都会造成不可预期的异常。下面是“Documentation\power\runtime\_pm.txt”中的解释，供大家参考：

> \* Once the subsystem-level suspend callback (or the driver suspend callback,   
>  if invoked directly) has completed successfully for the given device, the PM   
>  core regards the device as suspended, which need not mean that it has been   
>  put into a low power state. It is supposed to mean, however, that the   
>  device will not process data and will not communicate with the CPU(s) and   
>  RAM until the appropriate resume callback is executed for it. The runtime   
>  PM status of a device after successful execution of the suspend callback is   
>  'suspended'.

注2：回忆一下[wakeup events](/pm_subsystem/wakeup_events_framework.html)和[wakeup lock](/pm_subsystem/wakelocks.html)，Runtime PM和它们在本质上是一样的，都是实时的向PM core报告“我不工作了，可以睡了”、“我要工作了，不能睡（或醒来吧）”。不同的是：wakeup events和RPM的报告者是内核空间drivers，而wakeup lock是用户空间进程；wakeup events和wakelock涉及的睡眠对象是整个系统，包括CPU和所有的devices，而RPM是一个一个独立的device（CPU除外，它由cpu idle模块处理，可看作RPM的特例）。

##### 3.2 get和put的时机

这个话题的本质是：device idle的判断标准是什么？

再回忆一下“[autosleep](/pm_subsystem/autosleep.html)”中有关“Opportunistic suspend”的讨论，对“Opportunistic suspend”而言，suspend时机的判断是相当困难的，因为整机的运行环境比较复杂。而每一个具体设备的idle，就容易多了，这就是Runtime PM的优势。回到这个话题上，对device而言，什么是idle？

device是通过用户程序为用户提供服务的，而服务的方式分为两种：接受指令，做事情（被动）；上报事件（主动，一般通过中断的方式）。因此，设备active的时间段，包括【接受指令，完成指令】和【事件到达，由driver记录下来】两个。除此之外的时间，包括driver从用户程序获得指令（以及相关的数据）、driver将事件（以及相关的数据）交给应用程序，都是idle时间。

那idle时间是否应立即suspend以节省功耗？不一定，要具体场景具体对待：例如网络传输，如果网络连接正常，那么在可预期的、很短的时间内，设备又会active（传输网络数据），如果频繁suspend，会降低性能，且不会省电；比如用户按键，具有突发性，因而可以考虑suspend；等等。

由于get和put正是设备idle状态的切换点，因此get和put的时机就容易把握了：

1）主动访问设备时，如写寄存器、发起数据传输等等，get，增加引用计数，告诉RPM core设备active；访问结束后，put，减小引用计数，告诉RPM core设备可能idle。

2）设备有事件通知时，get（可能在中断处理中）；driver处理完事件后，put。

注3：以上只是理论场景，实际可以放宽，以减小设计的复杂度。

##### 3.3 异步（ASYNC）和同步（SYNC）

设备驱动代码可在进程和中断两种上下文执行，因此put和get等接口，要么是由用户进程调用，要么是由中断处理函数调用。由于这些接口可能会执行device的.runtime\_xxx回调函数，而这些接口的执行时间是不确定的，有些可能还会睡眠等待。这对用户进程或者中断处理函数来说，是不能接受的。

因此，RPM core提供的默认接口（pm\_runtime\_get/pm\_runtime\_put等），采用异步调用的方式（由ASYNC flag表示），启动一个work queue，在单独的线程中，调用.runtime\_xxx回调函数，这可以保证设备驱动之外的其它模块正常运行。

另外，如果设备驱动清楚地知道自己要做什么，也可以使用同步接口（pm\_runtime\_get\_sync/pm\_runtime\_put\_sync等），它们会直接调用.runtime\_xxx回调函数，不过，后果自负！

##### 3.4 Runtime PM过程中的同步问题

由于.runtime\_xxx回调函数可能采用异步的形式调用，以及Generic PM suspend和RPM并存的现状，要求RPM要小心处理同步问题，包括：

> 多个.runtime\_suspend请求之间的同步；   
> 多个.runtime\_resume请求之间的同步；   
> 多个.runtime\_idle请求之间的同步；   
> .runtime\_suspend请求和.runtime\_resume请求之间的同步；   
> .runtime\_suspend请求和system suspend之间的同步；   
> .runtime\_resume请求和system resume之间的同步；   
> 等等。

由此可知，RPM core将会有相当一部分代码，用来处理同步问题。

##### 3.5 级联设备之间的Runtime PM

struct device结构中，有一个parent指针，指向该设备的父设备（没有的话为空）。父设备通常是Bus、host controller，设备的正常工作，依赖父设备。体现在RPM中，就是如下的行为：

1）parent设备下任何一个设备处于active状态，parent必须active。

2）parent设备下任何一个设备idle了，要通知parent，parent以此记录处于active状态的child设备个数。

3）parent设备下所有子设备都idle了，parent才可以idle。

以上行为RPM core会自动处理，不需要驱动工程师太过操心。

##### 3.6 device的runtime status及其初始状态

在Runtime Power Management的过程中，device可处于四种状态：RPM\_ACTIVE、RPM\_RESUMING、RPM\_SUSPENDED和RPM\_SUSPENDING。

> RPM\_ACTIVE，设备处于正常工作的状态，表示设备的.runtime\_resume回调函数执行成功；
>
> RPM\_SUSPENDED，设备处于suspend状态，表示设备.runtime\_suspend回调函数执行成功；
>
> RPM\_RESUMING，设备的.runtime\_resume正在被执行；
>
> RPM\_SUSPENDING，设备的.runtime\_suspend正在被执行。
>
> 注4：前面说过，.runtime\_idle只是suspend前的过渡，因此runtime status和idle无关。

device注册时，设备模型代码会调用pm\_runtime\_init接口，将设备的runtime status初始化为RPM\_SUSPENDED，而kernel并不知道某个设备初始化时的真正状态，因此设备驱动需要根据实际情况，调用RPM的helper函数，将自身的status设置正确。

#### 4. runtime PM的API汇整

RPM提供的API位于“include/linux/pm\_runtime.h”中，在这里先浏览一下，目的有二：一是对前面描述的RPM运行机制有一个感性的认识；二是为后面分析RPM的运行机制做准备。

注5：我会把和驱动编写相关度较高的API加粗，其它的能不用就不用、能不看就不看！

extern int \_\_pm\_runtime\_idle(struct device \*dev, int rpmflags);   
extern int \_\_pm\_runtime\_suspend(struct device \*dev, int rpmflags);   
extern int \_\_pm\_runtime\_resume(struct device \*dev, int rpmflags);

> 这三个函数是RPM的idle、put/suspend、get/resume等操作的基础，根据rpmflag，有着不同的操作逻辑。后续很多API，都是基于它们三个。一般不会在设备驱动中直接使用。

**extern int pm\_schedule\_suspend(struct device \*dev, unsigned int delay);**

> 在指定的时间后（delay，单位是ms），suspend设备。该接口为异步调用，不会更改设备的引用计数，可在driver的.rpm\_idle中调用，免去driver自己再启一个timer的烦恼。

**extern void pm\_runtime\_enable(struct device \*dev);   
extern void pm\_runtime\_disable(struct device \*dev);**
> 设备RPM功能的enable/disable，可嵌套调用，会使用一个变量（dev->power.disable\_depth）记录disable的深度。只要disable\_depth大于零，就意味着RPM功能不可使用，很多的API调用（如suspend/reesume/put/get等）会返回失败。
>
> RPM初始化时，会将所有设备的disable\_depth置为1，也就是disable状态，driver初始化完毕后，要根据设备的时机状态，调用这两个函数，将RPM状态设置正确。

extern void pm\_runtime\_allow(struct device \*dev);   
extern void pm\_runtime\_forbid(struct device \*dev);

> RPM core通过sysfs（drivers/base/power/sysfs.c），为每个设备提供一个“/sys/devices/.../power/control”文件，通过该文件可让用户空间程序直接访问device的RPM功能。这两个函数用来控制是否开启该功能（默认开启）。

extern int pm\_runtime\_barrier(struct device \*dev);

> 这名字起的！！！
>
> 由3.3的描述可知，很多RPM请求都是异步的，这些请求会挂到一个名称为“pm\_wq”的工作队列上，这个函数的目的，就是清空这个队列，另外如果有resume请求，同步等待resume完成。好复杂，希望driver永远不要用到它！！

extern int pm\_generic\_runtime\_idle(struct device \*dev);   
extern int pm\_generic\_runtime\_suspend(struct device \*dev);   
extern int pm\_generic\_runtime\_resume(struct device \*dev);

> 几个通用的函数，一般给subsystem的RPM driver使用，直接调用devie driver的相应的callback函数。

extern void pm\_runtime\_no\_callbacks(struct device \*dev);

> 告诉RPM core自己没有回调函数，不用再调用了（或者调用都是成功的），真啰嗦。

extern void pm\_runtime\_irq\_safe(struct device \*dev);

> 告诉RPM core，如下函数可以在中断上下文调用：   
> pm\_runtime\_idle()   
> pm\_runtime\_suspend()   
> pm\_runtime\_autosuspend()   
> pm\_runtime\_resume()   
> pm\_runtime\_get\_sync()   
> pm\_runtime\_put\_sync()   
> pm\_runtime\_put\_sync\_suspend()   
> pm\_runtime\_put\_sync\_autosuspend()

static inline int pm\_runtime\_idle(struct device \*dev)   
static inline int pm\_runtime\_suspend(struct device \*dev)   
static inline int pm\_runtime\_resume(struct device \*dev)

> 直接使用同步的方式，尝试idle/suspend/resume设备，如果条件许可，就会执行相应的callback函数。driver尽量不要使用它们。

static inline int pm\_request\_idle(struct device \*dev)   
static inline int pm\_request\_resume(struct device \*dev)

> 和上面类似，不过调用方式为异步。尽量不要使用它们。

**static inline int pm\_runtime\_get(struct device \*dev)   
static inline int pm\_runtime\_put(struct device \*dev)**

> 增加/减少设备的使用计数，并判断是否为0，如果为零，尝试调用设备的idle callback，如果不为零，尝试调用设备的resume callback。
>
> 这两个接口是RPM的正统接口啊，多多使用！

static inline int pm\_runtime\_get\_sync(struct device \*dev)   
static inline int pm\_runtime\_put\_sync(struct device \*dev)   
static inline int pm\_runtime\_put\_sync\_suspend(struct device \*dev)

> 和上面类似，只不过为同步调用。另外提供了一个可直接调用suspend的put接口，何必的！

static inline int pm\_runtime\_autosuspend(struct device \*dev)   
static inline int pm\_request\_autosuspend(struct device \*dev)   
static inline int pm\_runtime\_put\_autosuspend(struct device \*dev)   
static inline int pm\_runtime\_put\_sync\_autosuspend(struct device \*dev)

> autosuspend相关接口。所谓的autosuspend，就是在suspend的基础上，增加一个timer，还是觉得有点啰嗦。不说了。

static inline void pm\_runtime\_use\_autosuspend(struct device \*dev)   
static inline void pm\_runtime\_dont\_use\_autosuspend(struct device \*dev)   
extern void pm\_runtime\_set\_autosuspend\_delay(struct device \*dev, int delay);   
extern unsigned long pm\_runtime\_autosuspend\_expiration(struct device \*dev);

> 控制是否使用autosuspend功能，以及设置/获取autosuspend的超时值。

总结一下：总觉得这些API所提供的功能有些重叠，重叠的有点啰嗦。可能设计者为了提供更多的便利，可过渡的便利和自由，反而是一种束缚和烦恼！

#### 5. runtime PM的使用步骤

觉得上面已经讲了，就不再重复了。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/rpm_overview.html)。*
