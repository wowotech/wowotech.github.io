---
title: "Linux电源管理(6)_Generic PM之Suspend功能"
date: 2014-08-22T21:40:34+08:00
url: "/pm_subsystem/suspend_and_resume.html"
gid: "81"
emlog_type: "blog"
summary: "Linux内核提供了三种Suspend: Freeze、Standby和STR(Suspend to RAM)，在用户空间向”/sys/power/state”文件分别写入”freeze”、”standby”和”mem”，即可触发它们。 内核中，Suspend及Resume过程涉及到PM Core、Device PM、各个设备的驱动、Platform dependent PM、CPU contro"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "内核", "suspend", "电源管理", "resume"]
views: 150701
comment_count: 121
aliases:
  - "/pm_subsystem/81.html"
  - "/81.html"
---

## 1. 前言

Linux内核提供了三种Suspend: Freeze、Standby和STR(Suspend to RAM)，在用户空间向”/sys/power/state”文件分别写入”freeze”、”standby”和”mem”，即可触发它们。

内核中，Suspend及Resume过程涉及到PM Core、Device PM、各个设备的驱动、Platform dependent PM、CPU control等多个模块，涉及了console switch、process freeze、CPU hotplug、wakeup处理等过个知识点。就让我们跟着内核代码，一一见识它们吧。

## 2. Suspend功能有关的代码分布

内核中Suspend功能有关的代码包括PM core、Device PM、Platform PM等几大块，具体如下：

1）PM Core

> kernel/power/main.c----提供用户空间接口(/sys/power/state)
>
> kernel/power/suspend.c----Suspend功能的主逻辑
>
> kernel/power/suspend\_test.c----Suspend功能的测试逻辑
>
> kernel/power/console.c----Suspend过程中对控制台的处理逻辑
>
> kernel/power/process.c----Suspend过程中对进程的处理逻辑

2）Device PM

> drivers/base/power/\*----具体可参考“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”的描述。
>
> 设备驱动----具体设备驱动的位置，不再涉及。

3）Platform dependent PM

> include/linux/suspend.h----定义platform dependent PM有关的操作函数集
>
> arch/xxx/mach-xxx/xxx.c或者
>
> arch/xxx/plat-xxx/xxx.c----平台相关的电源管理操作

## 3. suspend&resume过程概述

下面图片对Linux suspend&resume过程做了一个概述，读者可以顺着这个流程阅读内核源代码。具体的说明，可以参考后面的代码分析。

[![suspend_flow](/content/uploadfile/201408/ec1bf5143f7fe6d2b0b02d9c5557259f20140822134033.gif "suspend_flow")](/content/uploadfile/201408/d7d8826b98dcd42ff63de66398709a9a20140822134032.gif)

## 4. 代码分析

### 4.1 suspend入口

在用户空间执行如下操作：

> echo "freeze" > /sys/power/state
>
> echo "standby" > /sys/power/state
>
> echo "mem" > /sys/power/state

会通过sysfs触发suspend的执行，相应的处理代码如下：

```
static ssize_t state_store(struct kobject *kobj, struct kobj_attribute *attr,
                           const char *buf, size_t n)
{
        suspend_state_t state;
        int error;

        error = pm_autosleep_lock();
        if (error)
                return error;

        if (pm_autosleep_state() > PM_SUSPEND_ON) {
                error = -EBUSY;
                goto out;
        }

        state = decode_state(buf, n);
        if (state < PM_SUSPEND_MAX)
                error = pm_suspend(state);
        else if (state == PM_SUSPEND_MAX)
                error = hibernate();
        else
                error = -EINVAL;

 out:
        pm_autosleep_unlock();
        return error ? error : n;
}

power_attr(state);
```

power\_attr定义了一个名称为state的attribute文件，该文件的store接口为state\_store，该接口在lock住autosleep功能后，解析用户传入的buffer（freeze、standby or mem），转换成state参数。

state参数的类型为suspend\_state\_t，在include\linux\suspend.h中定义，为电源管理状态在内核中的表示。具体如下：

```
typedef int __bitwise suspend_state_t;

#define PM_SUSPEND_ON           ((__force suspend_state_t) 0)
#define PM_SUSPEND_FREEZE       ((__force suspend_state_t) 1)
#define PM_SUSPEND_STANDBY      ((__force suspend_state_t) 2)
#define PM_SUSPEND_MEM          ((__force suspend_state_t) 3)
#define PM_SUSPEND_MIN          PM_SUSPEND_FREEZE
#define PM_SUSPEND_MAX          ((__force suspend_state_t) 4)
```

根据state的值，如果不是（PM\_SUSPEND\_MAX，对应hibernate功能），则调用pm\_suspend接口，进行后续的处理。

pm\_suspend在kernel/power/suspend.c定义，处理所有的suspend过程。

## 4.2 pm\_suspend & enter\_state

pm\_suspend的实现非常简单，简单的做一下参数合法性判断，直接调用enter\_state接口，如下：

```
int pm_suspend(suspend_state_t state)
{
        int error;

        if (state <= PM_SUSPEND_ON || state >= PM_SUSPEND_MAX)
                return -EINVAL;

        error = enter_state(state);
        if (error) {
                suspend_stats.fail++;
                dpm_save_failed_errno(error);
        } else {
                suspend_stats.success++;
        }
        return error;
}
```

enter\_state代码为：

```
static int enter_state(suspend_state_t state)
{
        int error;

        if (!valid_state(state))
                return -ENODEV;

        if (!mutex_trylock(&pm_mutex))
                return -EBUSY;

        if (state == PM_SUSPEND_FREEZE)
                freeze_begin();

        printk(KERN_INFO "PM: Syncing filesystems ... ");
        sys_sync();
        printk("done.\n");

        pr_debug("PM: Preparing system for %s sleep\n", pm_states[state]);
        error = suspend_prepare(state);
        if (error)
                goto Unlock;

        if (suspend_test(TEST_FREEZER))
                goto Finish;

        pr_debug("PM: Entering %s sleep\n", pm_states[state]);
        pm_restrict_gfp_mask();
        error = suspend_devices_and_enter(state);
        pm_restore_gfp_mask();

 Finish:
        pr_debug("PM: Finishing wakeup.\n");
        suspend_finish();
 Unlock:
        mutex_unlock(&pm_mutex);
        return error;
}
```

主要工作包括：

a）调用valid\_state，判断该平台是否支持该电源状态。

suspend的最终目的，是让系统进入可恢复的挂起状态，而该功能必须有平台相关代码的参与才能完成，因此内核PM Core就提供了一系列的回调函数（封装在platform\_suspend\_ops中），让平台代码（如arch/arm/mach-xxx/pm.c）实现，然后由PM Core在合适的时机调用。这些回调函数包含一个valid函数，就是用来告知PM Core，支持哪些state。

最后看一下valid\_state的实现（删除了无关代码）：

```
bool valid_state(suspend_state_t state)
{
        if (state == PM_SUSPEND_FREEZE) {
                return true;
        }
        /*
         * PM_SUSPEND_STANDBY and PM_SUSPEND_MEMORY states need lowlevel
         * support and need to be valid to the lowlevel
         * implementation, no valid callback implies that none are valid.
         */
        return suspend_ops && suspend_ops->valid && suspend_ops->valid(state);
}
```

如果是freeze，无需平台代码参与即可支持，直接返回true。对于standby和mem，则需要调用suspend\_ops的valid回掉，由底层平台代码判断是否支持。

b）加互斥锁，只允许一个实例处理suspend。

c）如果state是freeze，调用freeze\_begin，进行suspend to freeze相关的特殊动作。我会在后面统一分析freeze的特殊动作，这里暂不描述。

d）打印提示信息，同步文件系统。

e）调用suspend\_prepare，进行suspend前的准备，主要包括switch console和process&thread freezing。如果失败，则终止suspend过程。

f）然后，调用suspend\_devices\_and\_enter接口，该接口负责suspend和resume的所有实际动作。前半部分，suspend console、suspend device、关中断、调用平台相关的suspend\_ops使系统进入低功耗状态。后半部分，在系统被事件唤醒后，处理相关动作，调用平台相关的suspend\_ops恢复系统、开中断、resume device、resume console。

g）最后，调用suspend\_finish，恢复（或等待恢复）process&thread，还原console。

**4.3 suspend\_prepare**

suspend\_prepare的代码如下：

```
static int suspend_prepare(suspend_state_t state)
{
        int error;

        if (need_suspend_ops(state) && (!suspend_ops || !suspend_ops->enter))
                return -EPERM;

        pm_prepare_console();

        error = pm_notifier_call_chain(PM_SUSPEND_PREPARE);
        if (error)
                goto Finish;

        error = suspend_freeze_processes();
        if (!error)
                return 0;

        suspend_stats.failed_freeze++;
        dpm_save_failed_step(SUSPEND_FREEZE);
 Finish:
        pm_notifier_call_chain(PM_POST_SUSPEND);
        pm_restore_console();
        return error;
}
```

主要工作为：

a）检查suspend\_ops是否提供了.enter回调，没有的话，返回错误。

b）调用pm\_prepare\_console，将当前console切换到一个虚拟console并重定向内核的kmsg（需要的话）。该功能称作VT switch，后面我会在稍微详细的介绍一下，但Linux控制台子系统是相当复杂的，更具体的分析，要在控制台子系统的分析文章中说明。

c）调用pm\_notifier\_call\_chain，发送suspend开始的消息（PM\_SUSPEND\_PREPARE），后面会详细描述。

d）调用suspend\_freeze\_processes，freeze用户空间进程和一些内核线程。该功能称作freezing-of-tasks，我会专门用一篇文章去分析它。本文就不再详细说明了。

e）如果freezing-of-tasks失败，调用pm\_restore\_console，将console切换回原来的console，并返回错误，以便能终止suspend。

**4.4 suspend\_devices\_and\_enter**

suspend\_devices\_and\_enter的过程较为复杂，代码实现如下：

```
int suspend_devices_and_enter(suspend_state_t state)
{
        int error;
        bool wakeup = false;

        if (need_suspend_ops(state) && !suspend_ops)
                return -ENOSYS;

        trace_machine_suspend(state);
        if (need_suspend_ops(state) && suspend_ops->begin) {
                error = suspend_ops->begin(state);
                if (error)
                        goto Close;
        }
        suspend_console();
        ftrace_stop();
        suspend_test_start();
        error = dpm_suspend_start(PMSG_SUSPEND);
        if (error) {
                printk(KERN_ERR "PM: Some devices failed to suspend\n");
                goto Recover_platform;
        }
        suspend_test_finish("suspend devices");
        if (suspend_test(TEST_DEVICES))
                goto Recover_platform;

        do {
                error = suspend_enter(state, &wakeup);
        } while (!error && !wakeup && need_suspend_ops(state)
                && suspend_ops->suspend_again && suspend_ops->suspend_again());

 Resume_devices:
        suspend_test_start();
        dpm_resume_end(PMSG_RESUME);
        suspend_test_finish("resume devices");
        ftrace_start();
        resume_console();
 Close:
        if (need_suspend_ops(state) && suspend_ops->end)
                suspend_ops->end();
        trace_machine_suspend(PWR_EVENT_EXIT);
        return error;

 Recover_platform:
        if (need_suspend_ops(state) && suspend_ops->recover)
                suspend_ops->recover();
        goto Resume_devices;
}
```

a）再次检查平台代码是否需要提供以及是否提供了suspend\_ops。

b）调用suspend\_ops的begin回调（有的话），通知平台代码，以便让其作相应的处理（需要的话）。可能失败，需要跳至Close处执行恢复操作（suspend\_ops->end）。

c）调用suspend\_console，挂起console。该接口由"kernel\printk.c"实现，主要是hold住一个lock，该lock会阻止其它代码访问console。

d）调用ftrace\_stop，停止ftrace功能。ftrace是一个很有意思的功能，后面再介绍。

e）调用dpm\_suspend\_start，调用所有设备的->prepare和->suspend回调函数（具体可参考“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”的描述），suspend需要正常suspend的设备。suspend device可能失败，需要跳至 Recover\_platform，执行recover操作（suspend\_ops->recover）。

f）以上都是suspend前的准备工作，此时，调用suspend\_enter接口，使系统进入指定的电源状态。该接口的内容如下：

```
static int suspend_enter(suspend_state_t state, bool *wakeup)
{
        int error;

        if (need_suspend_ops(state) && suspend_ops->prepare) {
                error = suspend_ops->prepare();
                if (error)
                        goto Platform_finish;
        }

        error = dpm_suspend_end(PMSG_SUSPEND);
        if (error) {
                printk(KERN_ERR "PM: Some devices failed to power down\n");
                goto Platform_finish;
        }

        if (need_suspend_ops(state) && suspend_ops->prepare_late) {
                error = suspend_ops->prepare_late();
                if (error)
                        goto Platform_wake;
        }

        if (suspend_test(TEST_PLATFORM))
                goto Platform_wake;

        /*
         * PM_SUSPEND_FREEZE equals
         * frozen processes + suspended devices + idle processors.
         * Thus we should invoke freeze_enter() soon after
         * all the devices are suspended.
         */
        if (state == PM_SUSPEND_FREEZE) {
                freeze_enter();
                goto Platform_wake;
        }

        error = disable_nonboot_cpus();
        if (error || suspend_test(TEST_CPUS))
                goto Enable_cpus;

        arch_suspend_disable_irqs();
        BUG_ON(!irqs_disabled());

        error = syscore_suspend();
        if (!error) {
                *wakeup = pm_wakeup_pending();
                if (!(suspend_test(TEST_CORE) || *wakeup)) {
                        error = suspend_ops->enter(state);
                        events_check_enabled = false;
                }
                syscore_resume();
        }

        arch_suspend_enable_irqs();
        BUG_ON(irqs_disabled());

 Enable_cpus:
        enable_nonboot_cpus();

 Platform_wake:
        if (need_suspend_ops(state) && suspend_ops->wake)
                suspend_ops->wake();

        dpm_resume_start(PMSG_RESUME);

 Platform_finish:
        if (need_suspend_ops(state) && suspend_ops->finish)
                suspend_ops->finish();

        return error;
}
```

f1）该接口处理完后，会通过返回值告知是否enter成功，同时通过wakeup指针，告知调用者，是否有wakeup事件发生，导致电源状态切换失败。

f2）调用suspend\_ops的prepare回调（有的话），通知平台代码，以便让其在即将进行状态切换之时，再做一些处理（需要的话）。该回调可能失败（平台代码出现意外），失败的话，需要跳至Platform\_finish处，调用suspend\_ops的finish回调，执行恢复操作。

f3）调用dpm\_suspend\_end，调用所有设备的->suspend\_late和->suspend\_noirq回调函数（具体可参考“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”的描述），suspend late suspend设备和需要在关中断下suspend的设备。需要说明的是，这里的noirq，是通过禁止所有的中断线的形式，而不是通过关全局中断的方式。同样，该操作可能会失败，失败的话，跳至Platform\_finish处，执行恢复动作。

f4）调用suspend\_ops的prepare\_late回调（有的话），通知平台代码，以便让其在最后关头，再做一些处理（需要的话）。该回调可能失败（平台代码出现意外），失败的话，需要跳至Platform\_wake处，调用suspend\_ops的wake回调，执行device的resume、调用suspend\_ops的finish回调，执行恢复操作。

f5）如果是suspend to freeze，执行相应的操作，包括冻结进程、suspended devices（参数为PM\_SUSPEND\_FREEZE）、cpu进入idle。如果有任何事件使CPU从idle状态退出，跳至Platform\_wake处，执行wake操作。

f6）调用disable\_nonboot\_cpus，禁止所有的非boot cpu。也会失败，执行恢复操作即可。

f7）调用arch\_suspend\_disable\_irqs，关全局中断。如果无法关闭，则为bug。

f8）调用syscore\_suspend，suspend system core。同样会失败，执行恢复操作即可。有关syscore，我会在另一篇文章中详细描述。

f9）如果很幸运，以上操作都成功了，那么，切换吧。不过，别高兴太早，还得调用pm\_wakeup\_pending检查一下，这段时间内，是否有唤醒事件发生，如果有就要终止suspend。

f10）如果一切顺利，调用suspend\_ops的enter回调，进行状态切换。这时，系统应该已经suspend了……

f11）suspend过程中，唤醒事件发生，系统唤醒，该函数接着执行resume动作，并最终返回。resume动作基本上是suspend的反动作，就不再继续分析了。

f12）或者，由于意外，suspend终止，该函数也会返回。

g）suspend\_enter返回，如果返回原因不是发生错误，且不是wakeup事件。则调用suspend\_ops的suspend\_again回调，检查是否需要再次suspend。再什么情况下要再次suspend呢？需要看具体的平台了，谁知道呢。

h）继续resume操作，resume device、start ftrace、resume console、suspend\_ops->end等等。

i）该函数返回后，表示系统已经resume。

**4.5 suspend\_finish**

比较简单：

```
static void suspend_finish(void)
{
        suspend_thaw_processes();
        pm_notifier_call_chain(PM_POST_SUSPEND);
        pm_restore_console();
}
```

a）恢复所有的用户空间进程和内核线程。

b）发送suspend结束的通知。

c）将console切换回原来的。

**5. 重要知识点回顾**

### **5.1 VT switch**

通常情况下，系统控制台模块（drivers\tty\vt\）会在suspend的过程中，重新分配一个console，并将控制台切换到该console上。然后在resume时，切换回旧的console。这就是VT switch功能。VT switch是很耗时的，因此内核提供了一些机制，控制是否使用这个功能：

1）提供一个接口函数pm\_set\_vt\_switch（drivers\tty\vt\vt\_ioctl.c），方便其它内核模块从整体上关闭或者开启VT switch功能。

2）VT switch全局开关处于开启状态时，满足如下的一种条件（可参考kernel\power\console.c相关的描述），即会使能VT switch

a）有console driver调用pm\_vt\_switch\_required接口，显式的要求使能VT switch。PM core的console模块会把这些信息记录在一个名称为pm\_vt\_switch\_list的链表中。

b）系统禁止在suspend的过程中suspend console（由kernel/printk.c中的console\_suspend\_enabled变量控制）。很有可能需要使用console查看suspend过程，此时为了使console不混乱，有必要进行VT switch。

c）没有任何console driver关心是否需要VT switch，换句话说没有任何driver调用pm\_vt\_switch\_required接口要求使能或禁止VT switch功能。此时会按照旧的习惯，进行VT switch。

因此，suspend过程对console的处理分为4步：

prepare console：负责在需要VT swich时，将当前console切换到SUSPEND console。

```
int pm_prepare_console(void)
{
        if (!pm_vt_switch())
                return 0;

        orig_fgconsole = vt_move_to_console(SUSPEND_CONSOLE, 1);
        if (orig_fgconsole < 0)
                return 1;

        orig_kmsg = vt_kmsg_redirect(SUSPEND_CONSOLE);
        return 0;
}
```

suspend console：挂起console，由kernel/printk.c实现，主要是hold住console用的互斥锁，使他人无法使用console。

resume console：对console解锁。

restore console：将console恢复为初始的console。

```
void pm_restore_console(void)
{
        if (!pm_vt_switch())
                return;

        if (orig_fgconsole >= 0) {
                vt_move_to_console(orig_fgconsole, 0);
                vt_kmsg_redirect(orig_kmsg);
        }
}
```

也许，您会问，why VT switch？先留着这个疑问吧，等到分析控制台时再回答。

### **5.2 freezing of task**

进程的freezing功能，是suspend、hibernate等电源管理功能的组成部分，在新版本内核中，它被独立出来，作为一个独立的电源管理状态（freeze）。该功能的目的，是在电源管理的状态切换过程中，确保所有用户空间进程和部分内核线程处于一个稳定的状态。有关该功能的具体描述，请参考wowotech后续的文章。

### **5.3 PM notifier**

PM notifier是基于内核blocking notifier功能实现的。blocking notifier提供了一种kernel内部的消息通知机制，消息接受者通过notifier注册的方式，注册一个回调函数，关注消息发送者发出的notifier。当消息产生时，消息产生者通过调用回调函数的形式，通知消息接受者。这种调用，是可以被阻塞的，因此称作blocking notifier。

那suspend功能为什么使用notifier呢？原因可能有多种，这里我举一个例子，这是我们日常开发中可能会遇到的。

由之前的描述可知，suspend过程中，suspend device发生在进程被freeze之后，resume device发生在进程被恢复之前。那么：

1）如果有些设备就需要在freeze进程之前suspend怎么办？

2）如果有些设备的resume动作需要较多延时，或者要等待什么事情发生，那么如果它的resume动作发生在进程恢复之前，岂不是要阻止所有进程的恢复？更甚者，如果该设备要等待某个进程的数据才能resume，怎么办？

再来看suspend\_prepare和suspend\_finish中的处理：

```
static int suspend_prepare(suspend_state_t state) {
…
        error = pm_notifier_call_chain(PM_SUSPEND_PREPARE);
        if (error)
                goto Finish;

        error = suspend_freeze_processes();
        …
}

static void suspend_finish(void)
{
        suspend_thaw_processes();
        pm_notifier_call_chain(PM_POST_SUSPEND);
        pm_restore_console();
}
```

原来PM notifier是在设备模型的框架外，开了一个后门，那些比较特殊的driver，可以绕过设备模型，直接接收PM发送的suspend信息，以便执行自身的suspend动作。特别是resume时，可以在其它进程都正好工作的时候，只让suspend进程等待driver的resume。

感兴趣的读者，可以围观一下下面这个活生生的例子（顺便提一下，好的设计是不应该有例外的）：

drivers\video\omap2\dss\core.c

### **5.4 device PM ops 和****platform PM ops****的调用时机**

对Linux驱动工程师来说，device PM ops和platform PM ops就是电源管理（suspend）的全部，只要在合适的地方，实现合适的回调函数，即可实现系统的电源管理。但现实太复杂了，以至于kernel提供的这两个数据结构也很复杂，再回忆一下，如下：

```
struct dev_pm_ops {
        int (*prepare)(struct device *dev);
        void (*complete)(struct device *dev);
        int (*suspend)(struct device *dev);
        int (*resume)(struct device *dev);
        int (*freeze)(struct device *dev);
        int (*thaw)(struct device *dev);
        int (*poweroff)(struct device *dev);
        int (*restore)(struct device *dev);
        int (*suspend_late)(struct device *dev);
        int (*resume_early)(struct device *dev);
        int (*freeze_late)(struct device *dev);
        int (*thaw_early)(struct device *dev);
        int (*poweroff_late)(struct device *dev);
        int (*restore_early)(struct device *dev);
        int (*suspend_noirq)(struct device *dev);
        int (*resume_noirq)(struct device *dev);
        int (*freeze_noirq)(struct device *dev);
        int (*thaw_noirq)(struct device *dev);
        int (*poweroff_noirq)(struct device *dev);
        int (*restore_noirq)(struct device *dev);
        int (*runtime_suspend)(struct device *dev);
        int (*runtime_resume)(struct device *dev);
        int (*runtime_idle)(struct device *dev);
};

struct platform_suspend_ops {
        int (*valid)(suspend_state_t state);
        int (*begin)(suspend_state_t state);
        int (*prepare)(void);
        int (*prepare_late)(void);
        int (*enter)(suspend_state_t state);
        void (*wake)(void);
        void (*finish)(void);
        bool (*suspend_again)(void);
        void (*end)(void);
        void (*recover)(void);
};
```

虽然内核的注释已经相当详细了，但我们一定会犯晕，到底该实现哪些回调？这些回调的应用场景又是什么？蜗蜗以为，要熟练使用这些回调，唯一的方法就是多coding、多理解。除此之外，我们可以总结一下在电源状态切换时，这些回调的调用时机，从侧面帮助理解。如下（只介绍和suspend功能有关的，struct dev\_pm\_ops简称D，struct platform\_suspend\_ops简称P）：

[![pm_ops_flow](/content/uploadfile/201408/b6884309987aaf29cb4212c290e2ae8920140822135346.gif "pm_ops_flow")](/content/uploadfile/201408/63ee3ab38963489e40787f14378fb39620140822135344.gif)

### **5.5 suspend过程的同步和****PM wakeup**

最重要的事情，如果suspend的过程中，有唤醒事件产生怎么办？正常的流程，应该终止suspend，返回并处理事件。但由于suspend过程的特殊性，进程被freeze、关中断等等，导致事情并没有那么简单，以至于在很久的一段时间内，kernel都不能很好的处理。这也称作suspend过程的同步问题。

在美好的旧时光里，suspend大多用于热关机，因此同步问题的影响并不突出(因为操作并不频繁)。但来到新时代之后，事情变了，Android竟然用suspend作日常的待机（操作就相当频繁了），这时问题就大了。那怎么解决呢？得靠system wakeup framework，也就是suspend过程中所调用的pm\_wakeup\_pending接口所在的模块。我会在下一篇文章中继续该模块的分析，这里就不再继续了。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/suspend_and_resume.html)。*
