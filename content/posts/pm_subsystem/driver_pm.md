---
title: "Linux电源管理(13)_Driver的电源管理"
date: 2014-12-26T18:31:51+08:00
url: "/pm_subsystem/driver_pm.html"
gid: "131"
emlog_type: "blog"
summary: "首先，回想一下wowo电源管理系列文章中提到的几个PM特性： A. Wake Count/Wake Source B. Wake Lock C. Auto Sleep D. Runtime Suspend 这篇文章就简单简单整理一下以上特性的在Driver中的使用场景，理解可能有偏差，大家多指教。"
author: "Physh"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Kernel", "driver"]
views: 37957
comment_count: 32
aliases:
  - "/pm_subsystem/131.html"
  - "/131.html"
---

首先，回想一下wowo电源管理系列文章中提到的几个PM特性：

A. [WakeUP Count/WakeUp Source](/pm_subsystem/wakeup_count.html)

B. [Wake Lock](/pm_subsystem/wakelocks.html)

C. [Auto Sleep](/pm_subsystem/autosleep.html)

D. [Runtime Suspend](/pm_subsystem/rpm_overview.html)

这篇文章就简单简单整理一下以上特性的在Driver中的使用场景，理解可能有偏差，大家多指教。来看看这个几个特性的实现分别在内核代码树的位置：

WakeUp Count/WakeUp Source：

/linux/driver/base/power/wakeup.c

Wake Lock :

对用户层的：/linux/kernel/power/wakelock.c

对内核层的：/linux/include/linux/wakelock.h

Auto Sleep:

/linux/kernel/power/autosleep.c

Runtime Suspend:

/linux/driver/base/power/runtime.c

有关PM的，集中在/kernel/power/目录（PM Core），以及/driver/base/power/目录（PM Function）。一个个来看看在驱动中怎么用这些特性吧。

先来看看WakeUp Count/WakeUp Souce。

刚开始接触这个东西，总容易被Wake Souce这个关键词迷惑，第一反应是把这东西跟HW Wake Souce牵连起来，但其实这东西跟硬件没什么关系，只是一个软件抽象出来的一种设备属性，所以如果在驱动开发过程中，需要该设备具备将系统从Low Power Mode唤醒的功能，还是不要被这个特性的名字所迷惑为好。

那么，这个特性怎么使用呢？回想一下wowo描述这个特性时提到的，wakeup count的目的是为了解决同步问题，也即是为了解决”在睡眠的过程中，接收到事件而想退出睡眠“的问题以及判断“在用户层发起睡眠请求时，当前系统是否符合睡眠条件”，关于wakeup\_count在用户层的应用可以简单总结为如下代码：

```
#define WAKEUP_COUNT   "/sys/power/wakeup_count"
#define POWER_STATE      "/sys/power/state"

int ret;
int wakeup;
FILE *f_wakeup = fopen(WAKE_COUNT, "rb+");
FILE *f_state = fopne(POWER_STATE, "rb+");

do {
    fscanf(f_wakeup, "%d", &wakeup);
    ret = fprintf(f_wakeup, "%d", wakeup);
}while (ret < 0);

fprintf(f_state, "mem");
```

用户层的应用就不过多考虑了，这里主要看Driver层。那么，看看Driver中关于wc/ws的应用场景：1. 在事件处理完之前主动阻止suspend，有点类似于锁，关于这点的应用就是之后要提到的对内核层的wake lock；2. 系统已经suspend了，唤醒系统上报事件，并在时间处理完之前主动阻止suspend，这就跟硬件唤醒源有关系了，而且肯定跟中断有关系。

来看第一种应用：

```
#include <xxx.h>
...
#include <linux/platform_device.h>
#include <linux/pm_wakeup.h>


int xxx(struct device *dev)
{
	pm_stay_awake(dev);
	....
	pm_relax(dev);
	...
}

int xxx_probe(struct platform_device *pdev)
{
	struct device *dev = pdev->dev;
	...

	device_init_wakeup(dev, true);
	...
}

int __init xxx_init(void)
{
	return platform_driver_register(&xxx_device_driver);
}

module_initcall(xxx_init);
MODULE_LICENSE("GPL");

```

device\_init\_wakeup()给这个device赋予了ws的属性，并且在执行xxx()函数过程可以阻止系统休眠。这种是主观上的阻止，也即驱动开发者预见到这段代码执行过程中不能休眠，从而主动给PM Core报告事件，这种使用场景跟中断没有关系，可以根据需求在任何内核执行路径上报告事件，目的只是为了阻止休眠而已，需要注意的是，这种设置是没办法唤醒已经休眠的系统的。

接下来看一种比较迷惑的情况：

```
#include <xxx.h>
...
#include <linux/platform_device.h>
#include <linux/pm_wakeup.h>

struct device * dev;

int xxx_isr(int irq, void *dev_id)
{
	pm_stay_awake(dev);
	....
	pm_relax(dev);
	
	return IRQ_HANDLED;
}

int xxx_probe(struct platform_device *pdev)
{
	int ret;
	dev = pdev->dev;
	...
	ret = request_irq(irq, xxx_isr, xxx, xxx, xxx);
	...
	device_init_wakeup(dev, true);
	...
}

int __init xxx_init(void)
{
	return platform_driver_register(&xxx_device_driver);
}

module_initcall(xxx_init);
MODULE_LICENSE("GPL");
```

这种情况和IRQ有关，之前以为这么做了之后这个设备就具备硬件唤醒功能了，现在想想还真是....其实，这样做了也只能保证在ISR执行期间不会休眠而已，这个设备中断是否具备硬件唤醒功能和wc/ws还是没什么关系。

那么，当确实需要具备硬件唤醒功能，怎么办呢？这里就要谈及一个硬件概念，唤醒中断源。

这个硬件功能不同厂商的处理方法不一，如三星有些SoC从硬件电气性上就使得某些中断Pin具备了唤醒CPU的功能，再如CSR的SoC规定了只有若干个Pin可以作为唤醒Pin使用，而Atmel的SoC则采用了软件的方式来创造唤醒中断源，也即先将所有中断禁止，之后在使能开发者设置的唤醒中断。说这么多中断的事，是因为Suspend的最终形态是WFI，wait for interrupt。要具备硬件唤醒功能，好歹得是一个能到达CPU Core的中断才行，而这中间经过各级中断管理器，并不说只要是一个中断就能唤醒系统的。

那么，想要具备唤醒系统的功能，就要从中断上下功夫，如下：

```
#include <xxx.h>
...
#include <linux/platform_device.h>
#include <linux/pm_wakeup.h>

struct device * dev;

int xxx_isr(int irq, void *dev_id)
{
	pm_stay_awake(dev);
	....
	pm_relax(dev);	
	return IRQ_HANDLED;
}

int xxx_probe(struct platform_device *pdev)
{
	int ret;
	int irq;
	int flag;

	dev = pdev->dev;
	...
	ret = request_irq(irq, xxx_isr, flag | IRQF_NO_SUSPEND, xxx, xxx);
	...
	enable_irq_wake(irq);
	device_init_wakeup(dev, true);
	...
}

int __init xxx_init(void)
{
	return platform_driver_register(&xxx_device_driver);
}

module_initcall(xxx_init);
MODULE_LICENSE("GPL");
```

  

这段代码中对中断做了两个特殊的处理，一个是在申请中断时加上了IRQF\_NO\_SUSPEND, 另一个是irq\_enable\_wake(irq); 这两个函数都可以赋予IRQ唤醒系统的能力，前者是在suspend过程中dpm\_suspend\_noirq()->suspend\_devices\_irq()时保留IRQF\_NO\_SUSPEND类型的中断响应，而后者直接跟irq\_chip打交道，把唤醒功能的设置交由irq\_chip driver处理。在Atmel的BSP中，这一个过程只是对一个名为wakeups的变量做了位标记，以便其随后在plat\_form\_ops->enter()时重新使能该中断。从使用角度我觉得，irq\_enable\_wake()会是一个更为保险且灵活的方法，毕竟更为直接而且禁用唤醒功能方便，disable\_irq\_wake()即可。

关于Wake Lock的使用，可以参考关于wc/ws的使用场景的前两种情况, wake\_lock()只是对wc/ws应用的一种封装。

可以把wake\_lock()当做一种锁来用，其内部使用了\_\_pm\_stay\_awake()来使系统保持唤醒状态。别忘记，这还是一种开发者主观上的使用，即开发者希望wake\_lock() ---> wake\_unlock()期间系统不休眠，类似一种特殊的临界区。

同时，相对wc/ws，wake\_lock()更像是一种快捷方式，开发者不用去使能设备的唤醒属性，也不用再去主动上报事件，只要在希望保持唤醒的特殊临界区的前后使用wake lock就可以达到目的。

Auto Sleep跟Wake Lock是一对冤家，一个没事就让系统休眠，一个偏不让系统休眠。简单来讲，Auto Sleep就是一直尝试sleep，如通过条件不满足，比如有事件pending（这可能是用户层持有wake\_lock, driver持有wake lock，以及上报的pending时间还没有处理完），就返回，过一会再来尝试。所以，如果使能了Auto Sleep这个特性，那写驱动的时候就要考虑到某段代码是否允许休眠后起来接着运行，如果不能，就要使用wake\_lock()保护起来。毕竟Auto Sleep这个特性是对于Driver来说，是被动的，异步的，不可预期的，如果Driver不想让PM Core逮着机会就休眠，就干脆别让系统休眠，而是先把自己的事情处理完了再说。

Runtime Suspend相对Auto Sleep而言就是更为Driver主观的行为了，虽然不一定但可以预期，到在调用pm\_runtime\_put()之后该设备可能进入runtime\_idle的状态。runtime\_idle的行为是Driver确定的，之后的runtime\_suspend也是Driver确定的，PM Core只是在维持设备的引用计数，当确定设备空闲时调用Driver提供的接口，使得设备进入idle或suspend。

所以，开发者需要注意的事情，是保证设备的电源行为符合内核文档所描述的行为，即suspend的状态下，不占用CPU，不与主存交互等（但不一定需要进入low power mode），以及，使得设备的suspend/resume功能正常。另外就是同步问题，pm\_runtime\_put()之后的代码可能会在runtime\_idle之后执行，所以重要的代码等还是在pm\_runtime\_put()之前完成更好。

抛砖引玉，大家多讨论。
