---
title: "中断唤醒系统流程"
date: 2018-01-01T17:03:28+08:00
url: "/irq_subsystem/irq_handle_procedure.html"
gid: "418"
emlog_type: "blog"
summary: "1) 设备唤醒cpu之后是立即跳转中断向量表指定的位置吗？如果不是，那么是什么时候才会跳转呢？ 2) 已经跳转到中断服务函数开始执行代码，后续就会调用你注册的中断handle 代码吗？如果不是，那中断服务函数做什么准备呢？而你注册的中断handle又会在什么时候才开始执行呢？ 3) 假如register_thread_irq方式注册的threaded irq中调用msleep(1000)，睡眠1秒"
author: "smcdef"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["电源管理", "中断处理", "中断子系统", "中断唤醒"]
views: 49909
comment_count: 22
aliases:
  - "/irq_subsystem/418.html"
  - "/418.html"
---

1. 前言

曾几何时，不知道你是否想过外部中断是如何产生的呢？又是如何唤醒系统的呢？在项目中，一般具有中断唤醒的设备会有一个interrupt pin硬件连接到SoC的gpio pin。一般来说，当设备需要唤醒系统的时候，会通过改变interrupt pin电平状态，而SoC会检测到这个变化，将SoC从睡眠中唤醒，该设备通过相关的子系统通知上层应用做出相应的处理。这就是中断唤醒的过程。说起来很简洁，可以说是涵盖了软硬件两大块。是不是？

为了使能设备的唤醒能力，设备驱动中会在系统suspend的时候通过enable\_irq\_wake(irq)接口使能设备SoC引脚的中断唤醒能力。然后呢？然后当然是万事大吉了，静静的等待设备中断的到来，最后唤醒系统。假设我们做一款手机，手机有一个压感传感器，重压点亮屏幕，轻压在灭屏的时候无响应，在亮屏的时候作为home键功能，压力值通过i2c总线读取（描述挺像iPhone8的home键！）。假如有一天，你突然发现重压按键，屏幕不亮。于是你开始探究所以然，聪明的你一定会先去用示波器测量irq pin的波形，此时你发现了重压按键，的确产生了一个电平信号的变化，此时可就怪不得硬件了。而你又发现插入USB使用ADB工具抓取log的情况下（Android的adb工具需要通过USB协议通信，一般不会允许系统休眠），重压可以亮屏。此时，我觉得就很有可能是唤醒系统了，但是系统醒来后又睡下去了，而你注册的中断服务函数中的代码没有执行完成就睡了。什么情况下会出现呢？试想一下，你通过request\_irq接口注册的handle函数中queue work了一个延迟工作队列（主要干活的，类似下半部吧），由于时间太长，还没来得及调度呢，系统又睡下了，虽然你不愿意，但是事情就是可能这样发生的。那这一切竟然是为什么呢？作为驱动工程师最关注的恐怕就是如何避开这些问题呢？  
1) 设备唤醒cpu之后是立即跳转中断向量表指定的位置吗？如果不是，那么是什么时候才会跳转呢？  
2) 已经跳转到中断服务函数开始执行代码，后续就会调用你注册的中断handle 代码吗？如果不是，那中断服务函数做什么准备呢？而你注册的中断handle又会在什么时候才开始执行呢？  
3) 假如register\_thread\_irq方式注册的threaded irq中调用msleep(1000)，睡眠1秒，请问系统此时会继续睡下去而没调度回来吗？因此导致msleep后续的操作没有执行。  
4) 如果在注册的中断handle中把主要的操作都放在delayed work中，然后queue delayed work，work延时1秒执行，请问系统此时会继续睡下去而没调度delayed work 吗？因此导致delayed work 中的操作没有执行呢？  
5) 如果4)成立的话，我们该如何编程避免这个问题呢？  
好了，本片文章就为你解答所有的疑问。  
注：文章代码分析基于linux-4.15.0-rc3。

2. 中断唤醒流程

现在还是假设你有一个上述的设备，现在你开始编写driver代码了。假设部分代码如下：

```
static irqreturn_t smcdef_event_handler(int irq, void *private)
{
    /* do something you want, like report input events through input subsystem */

    return IRQ_HANDLED;
}

static int smcdef_suspend(struct device *dev)
{
    enable_irq_wake(irq);
}

static int smcdef_resume(struct device *dev)
{
    disable_irq_wake(irq);
}

static int smcdef_probe(struct i2c_client *client,
        const struct i2c_device_id *id)
{
    /* ... */
    request_thread_irq(irq,
            smcdef_event_handler,
            NULL,
            IRQF_TRIGGER_FALLING,
            "smcdef",
            pdata);

    return 0;
}

static int smcdef_remove(struct i2c_client *client)
{
    return 0;
}

static const struct of_device_id smcdef_dt_ids[] = {
    {.compatible = "wowo,smcdef" },
    { }
};
MODULE_DEVICE_TABLE(of, smcdef_dt_ids);

static SIMPLE_DEV_PM_OPS(smcdef_pm_ops, smcdef_suspend, smcdef_resume);

static struct i2c_driver smcdef_driver = {
    .driver = {
        .name             = "smcdef",
        .of_match_table = of_match_ptr(smcdef_dt_ids),
        .pm                = &smcdef_pm_ops,
    },
    .probe  = smcdef_probe,
    .remove = smcdef_remove,
};
module_i2c_driver(smcdef_driver);

MODULE_AUTHOR("smcdef");
MODULE_DESCRIPTION("IRQ test");
MODULE_LICENSE("GPL");
```

在probe函数中通过request\_thread\_irq接口注册驱动的中断服务函数smcdef\_event\_handler，注意这里smcdef\_event\_handler的执行环境是中断上下文，thread\_fn的方式下面也会介绍。

2.1. enable\_irq\_wake

当系统睡眠（echo "mem" > /sys/power/state）的时候，回想一下suspend的流程就会知道，最终会调用smcdef\_suspend使能中断唤醒功能。enable\_irq\_wake主要工作是在irq\_set\_irq\_wake中完成，代码如下：

```
int irq_set_irq_wake(unsigned int irq, unsigned int on) 
{
    unsigned long flags;
    struct irq_desc *desc = irq_get_desc_buslock(irq, &flags, IRQ_GET_DESC_CHECK_GLOBAL);
    int ret = 0;

    /* wakeup-capable irqs can be shared between drivers that
     * don't need to have the same sleep mode behaviors.
     */
    if (on) {
        if (desc->wake_depth++ == 0) {
            ret = set_irq_wake_real(irq, on);
            if (ret)
                desc->wake_depth = 0;
            else
                irqd_set(&desc->irq_data, IRQD_WAKEUP_STATE);
        }
    } else {
        if (desc->wake_depth == 0) {
            WARN(1, "Unbalanced IRQ %d wake disable\n", irq);
        } else if (--desc->wake_depth == 0) {
            ret = set_irq_wake_real(irq, on);
            if (ret)
                desc->wake_depth = 1;
            else
                irqd_clear(&desc->irq_data, IRQD_WAKEUP_STATE);
        }
    }
    irq_put_desc_busunlock(desc, flags);
    return ret;
}
```

> 1) 首先在set\_irq\_wake\_real函数中通过irq\_chip的irq\_set\_wake回调函数设置SoC相关wakeup寄存器使能中断唤醒功能，如果不使能的话，即使设备在那疯狂的产生中断signal，SoC可不会理睬你哦！  
> 2) 设置irq的state为IRQD\_WAKEUP\_STATE，这步很重要，suspend流程会用到的。

2.2. Suspend to RAM流程

先画个图示意一下系统Suspend to RAM流程。我们可以看到图片画的很漂亮。从enter\_state开始到suspend\_ops->enter()结束。对于suspend\_ops->enter()调用，我的理解是CPU停在这里了，待到醒来的时候，就从这里开始继续前行的脚步。

`![STR流程.png](/content/uploadfile/201801/7dc41514798124.png "点击查看原图")`

> 1) enable\_irq\_wake()可以有两种途径，一是在driver的suspend函数中由驱动开发者主动调用；二是在driver的probe函数中调用dev\_pm\_set\_wake\_irq()和device\_init\_wakeup()。因为suspend的过程中会通过dev\_pm\_arm\_wake\_irq()打开所有wakeup source的irq wake功能。我更推荐途径1，因为系统已经帮我们做了，何必重复造轮子呢！  
> 2) 对于已经enable 并且使能wakeup的irq，置位IRQD\_WAKEUP\_ARMED，然后等待IRQ handler和threaded handler执行完成。后续详细分析这一块。  
> 3) 针对仅仅enable的irq，设置IRQS\_SUSPENDED标志位，并disable irq。  
> 4) 图中第④步关闭noboot cpu，紧接着第⑤步diasble boot cpu的irq，即cpu不再响应中断。  
> 5) 在cpu sleep之前进行最后一步操作就是syscore suspend。既然是最后suspend，那一定是其他device都依赖的系统核心驱动。后面说说什么的设备会注册syscore suspend。

2.3. resume流程

假设我们使用的是gic-v3代码，边沿触发中断设备。现在设备需要唤醒系统了，产生一个边沿电平触发中断。此时会唤醒boot cpu（因为noboot cpu在suspend的时候已经被disable）。你以为此时就开始跳转中断服务函数了吗？no！还记得上一节说的吗？suspend之后已经diasble boot cpu的irq，因此中断不会立即执行。什么时候会执行呢？当然是等到local\_irq\_enable()之后。resume流程如下图。

![resume流程.png](/content/uploadfile/201801/a16a1514798123.png "点击查看原图")

> 1) 首先执行syscore resume，马上为你讲解syscore的用意。  
> 2) arch\_suspend\_enable\_irqs()结束后就会进入中断服务函数，因为中断打开了，interrupt controller的pending寄存器没有清除，因此触发中断。你以为此时会调用到你注册的中断handle吗？错了！此时中断服务函数还没执行你注册的handle就返回了。马上为你揭晓为什么。先等等。

先说到这里，先看看什么是syscore。

2.4. system core operations有什么用？

先想一想为什么要等到syscore\_resume之后才arch\_suspend\_enable\_irqs()呢？试想一下，系统刚被唤醒，最重要的事情是不是先打开相关的时钟以及最基本driver（例如：gpio、irq\_chip等）呢？因此syscore\_resume主要是clock以及gpio的驱动resume，因为这是其他设备依赖的最基本设备。回想一下上一节中Susoend to RAM流程中，syscore\_suspend也同样是最后suspend的，毕竟人家是大部分设备的基础，当然最后才能suspend。可以通过register\_syscore\_ops()接口注册syscore operation。

2.5. gic interrupt controller中断执行流程

接下来arch\_suspend\_enable\_irqs()之后就是中断流程了，其函数执行流程如下。

![中断执行流程.png](/content/uploadfile/201801/e8b41514798125.png "点击查看原图")

图片中是一个中断从汇编开始到结束的流程。假设我们的设备是边沿触发中断，那么一定会执行到handle\_edge\_irq()，如果你不想追踪代码，或者对中断流程不熟悉，我教你个方法，在注册的中断handle中加上一句WARN\_ON(1);语句，请查看log信息即可。handle\_edge\_irq()代码如下：

```
void handle_edge_irq(struct irq_desc *desc)
{
    raw_spin_lock(&desc->lock);

    desc->istate &= ~(IRQS_REPLAY | IRQS_WAITING);

    if (!irq_may_run(desc)) {
        desc->istate |= IRQS_PENDING;
        mask_ack_irq(desc);
        goto out_unlock;
    }

    /*
     * If its disabled or no action available then mask it and get
     * out of here.
     */
    if (irqd_irq_disabled(&desc->irq_data) || !desc->action) {
        desc->istate |= IRQS_PENDING;
        mask_ack_irq(desc);
        goto out_unlock;
    }

    kstat_incr_irqs_this_cpu(desc);

    /* Start handling the irq */
    desc->irq_data.chip->irq_ack(&desc->irq_data);

    do {
        if (unlikely(!desc->action)) {
            mask_irq(desc);
            goto out_unlock;
        }

        /*
         * When another irq arrived while we were handling
         * one, we could have masked the irq.
         * Renable it, if it was not disabled in meantime.
         */
        if (unlikely(desc->istate & IRQS_PENDING)) {
            if (!irqd_irq_disabled(&desc->irq_data) &&
                irqd_irq_masked(&desc->irq_data))
                unmask_irq(desc);
        }

        handle_irq_event(desc);

    } while ((desc->istate & IRQS_PENDING) &&
         !irqd_irq_disabled(&desc->irq_data));

out_unlock:
    raw_spin_unlock(&desc->lock);
}
```

> 1) irq\_may\_run()判断irq是否有IRQD\_WAKEUP\_ARMED标志位，当然这里是有的。随后调用irq\_pm\_check\_wakeup()清除IRQD\_WAKEUP\_ARMED flag顺便置位IRQS\_SUSPENDED和IRQS\_PENDING flag，又irq\_disable关闭了中断。  
> 2) irq\_may\_run()返回false，因此这里直接返回了，所以你注册的中断handle并没有执行。你绝望，也没办法。当然这里也可以知道，唤醒系统的这次中断注册的handle的执行环境不是硬件中断上下文。

2.6. dpm\_resume\_noirq()  

我们来继续分析2.3节resume的后续流程，把图继续搬过来。

![resume流程.png](/content/uploadfile/201801/a16a1514798123.png "点击查看原图")

> 1) 继续enable所有的noboot cpu之后，开始dpm\_resume\_noirq()。这里为什么起名noirq呢？中断已经可以响应了，我猜测是这样的：虽然可以响应中断，但是也是仅限于suspend之前的enable\_irq\_wake的irq，因为其他irq已经被disable。并且具有唤醒功能的irq也仅仅是进入中断后设置一些flag就立即退出了，没有执行irq handle，因此相当于noirq。  
> 2) dpm\_noirq\_resume\_devices()会调用"noirq" resume callbacks，这个就是struct dev\_pm\_ops结构体的resume\_noirq成员。那么什么的设备驱动需要填充resume\_noirq成员呢？我们考虑一个事情，到现在为止唤醒系统的irq的handle还没有执行，如果注册的中断handle是通过spi、i2c等方式通信，那么在即将执行之前，我们是不是应该首先resume spi、i2c等设备呢！所以说，很多设备依赖的设备，尽量填充resume\_noirq成员，这样才比较合理。毕竟唤醒的设备是要使用的嘛！而gpio驱动就适合syscore resume，因为这里i2c设备肯定依赖gpio设备。大家可以看看自己平台的i2c、spi等设备驱动是不是都实现resume\_noirq成员。当然了，前提是这个设备需要resume操作，如果不需要resume就可以使用，那么完全没有必要resume\_noirq。所以，写driver也是要考虑很多问题的，driver应该实现哪些dev\_pm\_ops的回调函数？  
> 3) resume\_device\_irqs中会帮我们把已经enable\_irq\_wake的设备进行disable\_irq\_wake，但是前提是driver中通过2.2节中途径1的方式。  
> 4) resume\_irqs继续调用，最终会enable所有在susoend中关闭的irq。  
> 5) check\_irq\_resend才是真正触发你注册的中断handle执行的真凶。

check\_irq\_resend代码如下:

```
void check_irq_resend(struct irq_desc *desc)
{
    /*
     * We do not resend level type interrupts. Level type
     * interrupts are resent by hardware when they are still
     * active. Clear the pending bit so suspend/resume does not
     * get confused.
     */
    if (irq_settings_is_level(desc)) {
        desc->istate &= ~IRQS_PENDING;
        return;
    }
    if (desc->istate & IRQS_REPLAY)
        return;
    if (desc->istate & IRQS_PENDING) {
        desc->istate &= ~IRQS_PENDING;
        desc->istate |= IRQS_REPLAY;

        if (!desc->irq_data.chip->irq_retrigger ||
            !desc->irq_data.chip->irq_retrigger(&desc->irq_data)) {

            unsigned int irq = irq_desc_get_irq(desc);

            /* Set it pending and activate the softirq: */
            set_bit(irq, irqs_resend);
            tasklet_schedule(&resend_tasklet);
        }
    }
}
```

由于在之前分析已经设置了IRQS\_PENDING flag，因此这里会tasklet\_schedule(&resend\_tasklet)并且置位irqs\_resend变量中相应的bit位，代表软中断触发。然后就开始tasklet\_schedule最终会唤醒ksoftirqd线程，在ksoftirqd线程中会调用你注册的中断handle。具体调用过程可以参考wowo的softirq和tasklet文章。这里我们也可以得出中断handle执行的上下文环境是软中断上下文的结论。当然我们还是有必要分析一下tasklet最后一步resend\_irqs()函数的作用，代码如下：

```
/* Bitmap to handle software resend of interrupts: */
static DECLARE_BITMAP(irqs_resend, IRQ_BITMAP_BITS);

/*
 * Run software resends of IRQ's
 */
static void resend_irqs(unsigned long arg)
{
    struct irq_desc *desc;
    int irq;

    while (!bitmap_empty(irqs_resend, nr_irqs)) {
        irq = find_first_bit(irqs_resend, nr_irqs);
        clear_bit(irq, irqs_resend);
        desc = irq_to_desc(irq);
        local_irq_disable();
        desc->handle_irq(desc);
        local_irq_enable();
    }
}
/* Tasklet to handle resend: */
static DECLARE_TASKLET(resend_tasklet, resend_irqs, 0);
```

> 1) irqs\_resend是一个unsigned int类型的数组，每一个bit都代表一个irq是否resend。  
> 2) resend\_irqs是注册的resend\_tasklet的callback函数，当tasklet\_schedule(&resend\_tasklet)之后就会被调度执行。  
> 3) 在resend\_irqs函数中，通过判断irqs\_resend变量中的每一个bit位是否为1（即是否需要resend，也就是调用irq注册的中断handle）。  
> 好了，现在可以解答清楚的解答第一个问题了：设备唤醒cpu之后是立即跳转中断向量表指定的位置吗？如果不是，那么是什么时候才会跳转呢？设备唤醒cpu之后并不是立即跳转中断向量执行中断，而是等到syscore\_resume以及打开cpu中断之后才开始。第二个问题也有答案了，已经跳转到中断服务函数开始执行代码，后续就会调用你注册的中断handle 吗？如果不是，那中断服务函数做什么准备呢？而你注册的中断handle又会在什么时候才开始执行呢？第一次跳转执行中断仅仅是设置相关的flag并且disable\_irq，在执行完成设备的resume noirq回调函数之后通过check\_irq\_resend中调度tasklet，最终执行注册的中断handle，至于为什么要这么做，前面分析也给了答案。

2.7. IRQ handler会睡眠吗？

你想过request\_thread\_irq函数注册的hardirq
handler或者是threaded handler会执行一半时，系统会再一次的休眠下去吗？再看看2.2节的图，实际上对于所有已经打开的irq在suspend\_device\_irqs()会调用synchronize\_irq()等待正在处理的hardirq
handler或者threaded handler。synchronize\_irq()代码如下：

```
void synchronize_irq(unsigned int irq)
{
    struct irq_desc *desc = irq_to_desc(irq);

    if (desc) {
        __synchronize_hardirq(desc);
        /*
         * We made sure that no hardirq handler is
         * running. Now verify that no threaded handlers are
         * active.
         */
        wait_event(desc->wait_for_threads,
               !atomic_read(&desc->threads_active));
    }
}
```

> 1) \_\_synchronize\_hardirq()是等待hardirq handler执行完毕。  
> 2) 只要threads\_active计数不为0就等待threaded handler执行完毕。

\_\_synchronize\_hardirq()代码如下：

```
static void __synchronize_hardirq(struct irq_desc *desc)
{
    bool inprogress;

    do {
        unsigned long flags;

        /*
         * Wait until we're out of the critical section.  This might
         * give the wrong answer due to the lack of memory barriers.
         */
        while (irqd_irq_inprogress(&desc->irq_data))
            cpu_relax();

        /* Ok, that indicated we're done: double-check carefully. */
        raw_spin_lock_irqsave(&desc->lock, flags);
        inprogress = irqd_irq_inprogress(&desc->irq_data);
        raw_spin_unlock_irqrestore(&desc->lock, flags);

        /* Oops, that failed? */
    } while (inprogress);
}
```

irqd\_irq\_inprogress()是判断irq是否设置了IRQD\_IRQ\_INPROGRESS 标志位。标识hardirq thread正在执行，IRQD\_IRQ\_INPROGRESS在handle\_irq\_event()执行开始设置，等到handle\_irq\_event\_percpu()执行完毕之后，同样在handle\_irq\_event()之后清除。因此hardirq handler执行结束之前系统不会睡眠。那么threaded handler情况也是这样吗？在\_\_handle\_irq\_event\_percpu()函数中通过\_\_irq\_wake\_thread()函数唤醒irq\_thread线程。\_\_irq\_wake\_thread()函数如下：

```
void __irq_wake_thread(struct irq_desc *desc, struct irqaction *action)
{
    /*
     * In case the thread crashed and was killed we just pretend that
     * we handled the interrupt. The hardirq handler has disabled the
     * device interrupt, so no irq storm is lurking.
     */
    if (action->thread->flags & PF_EXITING)
        return;

    /*
     * Wake up the handler thread for this action. If the
     * RUNTHREAD bit is already set, nothing to do.
     */
    if (test_and_set_bit(IRQTF_RUNTHREAD, &action->thread_flags))
        return;

    desc->threads_oneshot |= action->thread_mask;

    atomic_inc(&desc->threads_active);

    wake_up_process(action->thread);
}
```

> 1) 如果irq的中断线程已经设置IRQTF\_RUNTHREAD标志位，代表irq线程已经正在运行，因此无需重新唤醒，直接返回即可。  
> 2) 使用atomic\_inc()增加threads\_active计数，在synchronize\_irq()函数中会判断threads\_active计数是否为0来决定是否需要等待irq\_thread执行完毕。

说了这些，不知道你是否知道什么是irq\_thread呢？我们通过request\_thread\_irq()函数指定thread\_fn，这个thread\_fn就是irq\_thread线程最终调用的函数。而每个irq都会创建一个irq线程，创建的过程在setup\_irq\_thread()函数进行，setup\_irq\_thread()函数代码如下：

```
static int setup_irq_thread(struct irqaction *new, unsigned int irq, bool secondary)
{
    struct task_struct *t;
    struct sched_param param = {
        .sched_priority = MAX_USER_RT_PRIO/2,
    };

    if (!secondary) {
        t = kthread_create(irq_thread, new, "irq/%d-%s", irq, new->name);
    } else {
        t = kthread_create(irq_thread, new, "irq/%d-s-%s", irq, new->name);
        param.sched_priority -= 1;
    }

    if (IS_ERR(t))
        return PTR_ERR(t);

    sched_setscheduler_nocheck(t, SCHED_FIFO, &param);

    get_task_struct(t);
    new->thread = t;

    set_bit(IRQTF_AFFINITY, &new->thread_flags);
    return 0;
}
```

通过kthread\_create()创建irq/irq-new->name的线程，该线程的入口函数值irq\_thread。在irq\_thread()中每执行完成一个thread\_fn就会threads\_active计数减1。  
现在可以考虑第三个问题了，假如register\_thread\_irq方式注册的threaded irq中调用msleep(1000)，睡眠1秒，请问系统此时会继续睡下去而没调度回来吗？因此导致msleep后续的操作没有执行。答案就是不会，因为suspend时候会等待threaded handler执行完毕，所以系统不会睡眠，放心好了。

2.8. 工作队列会睡眠吗？

现在来思考一个按键消抖问题。如果你还不知道什么是按键消抖的话，我……。按键消抖在内核中通常是这样处理，通过变压触发中断，在中断handler中通过queue delayed work一段时间，计时结束执行按键上报处理。从内核的gpio\_keys抠出部分代码如下：

```
static void gpio_keys_gpio_work_func(struct work_struct *work)
{
    struct gpio_button_data *bdata =
        container_of(work, struct gpio_button_data, work.work);

    gpio_keys_gpio_report_event(bdata);
}

static irqreturn_t gpio_keys_gpio_isr(int irq, void *dev_id)
{
    struct gpio_button_data *bdata = dev_id;

    mod_delayed_work(system_wq,
             &bdata->work,
             msecs_to_jiffies(bdata->software_debounce));

    return IRQ_HANDLED;
}
```

当按键按下，中断handler gpio\_keys\_gpio\_isr执行，设定delayed work的定时器，等到定时器计时结束执行gpio\_keys\_gpio\_work\_func()，在gpio\_keys\_gpio\_work\_func()上报键值。你有考虑过一个问题吗？假如系统已经睡眠，此时第一次按下按键，是否有可能出现gpio\_keys\_gpio\_work\_func()函数没有执行，系统又继续睡眠，在第二次按键的时候执行第一次按键应该调用的gpio\_keys\_gpio\_work\_func()的情况吗？其实是有可能出现。只要bdata->software\_debounce大于一定的时间就有可能出现。如果这个时间巧合，还有可能出现有时候正确上报，有时候没有上报。其实原因就是，内核的suspend只保证了IRQ handler的执行完成，并没有保证工作队列的执行完毕。

这里说的问题是work\_queue没有机会调度，系统就休眠了。如果使用的不是delayed work，就是普通的work，只是在work中使用类似msleep的操作，系统是否也会继续睡眠呢？修改代码如下：

```
static void gpio_keys_gpio_work_func(struct work_struct *work)
{
    struct gpio_button_data *bdata =
        container_of(work, struct gpio_button_data, work.work);

	msleep(1000);
    gpio_keys_gpio_report_event(bdata);
}

static irqreturn_t gpio_keys_gpio_isr(int irq, void *dev_id)
{
    struct gpio_button_data *bdata = dev_id;

    schedule_work(&bdata->work);

    return IRQ_HANDLED;
}
```

这里的gpio\_keys\_gpio\_work\_func()中添加一句msleep(1000)会怎么样呢？由于此时使用的不是delayed work，因此一般不会出现没有调度work就睡眠的情况，与上面的情况还是有点区别的。但是这里其实也是有可能睡眠的，一旦msleep(1000)语句执行完毕，系统满足sleep条件，此时系统还是有可能睡眠导致后面的操作没有执行。在下次唤醒系统的时候才可能执行。所以这种情况下也是危险的。

结论就是：内核的suspend只保证了IRQ
handler（hardirq handler or threaded
handler）的执行完成，并没有保证工作队列的执行完毕。因此我们使用工作队列的话，必须要考虑这种情况的发生，并解决。

2.9. 如何解决工作队列睡眠问题？

系统suspend的过程中，主要是通过pm\_wakeup\_pending()判断suspend是否需要abort。如果你对我说的这一块不清楚，可以看看wowo其他几篇关于电源管理的文章。pm\_wakeup\_pending()主要是判断combined\_event\_count变量在suspend的过程中是否改变，如果改变suspend就应该abort。既然知道了原理，那么就好办了。在中断handler开始处增加combined\_event\_count计数，工作队列函数结尾位置减小combined\_event\_count计数即可。当然是不用你自己写代码，系统提供了接口函数pm\_stay\_awake()和pm\_relax()。2.8节修改后的代码如下：

```
static void gpio_keys_gpio_work_func(struct work_struct *work)
{
    struct gpio_button_data *bdata =
        container_of(work, struct gpio_button_data, work.work);

    gpio_keys_gpio_report_event(bdata);
    if (bdata->button->wakeup)
        pm_relax(bdata->input->dev.parent);
}

static irqreturn_t gpio_keys_gpio_isr(int irq, void *dev_id)
{
    struct gpio_button_data *bdata = dev_id;

    if (bdata->button->wakeup) {
        const struct gpio_keys_button *button = bdata->button;

        pm_stay_awake(bdata->input->dev.parent);
    }

    mod_delayed_work(system_wq,
             &bdata->work,
             msecs_to_jiffies(bdata->software_debounce));

    return IRQ_HANDLED;
}
```

好了，现在你放心好了，即使你是在gpio\_keys\_gpio\_work\_func()中msleep(2000)，系统也会等到pm\_relax()执行之后系统才可能suspend。

3. 驱动工程师建议

看了这么多代码总是想说点东西。不管是建议还是什么。我由衷地希望驱动工程师可以写出完美没有bug并且简洁的代码。因此，这里有点小建议给驱动工程师（某些特性可能需要比较新的内核版本）。  
1) 如果设备具有唤醒系统的功能，请在probe函数中调用device\_init\_wakeup()和dev\_pm\_set\_wake\_irq()（注意调用顺序，先device\_init\_wakeup()再dev\_pm\_set\_wake\_irq()）。毕竟这样系统suspend的时候会自动帮助我们enable\_irq\_wake()和disable\_irq\_wake()，何乐而不为呢！简单就是美。如果你是i2c设备，那么可以更完美。连probe函数里面也可以不用调用了。只需要在设备的dts中添加wakeup-source属性即可。i2c core会自动帮我们完成这些操作。  
2) 如果你习惯在driver的suspend()中关闭中断，在resum()中打开中断，我觉你没必要这么做，何必要这些冗余代码呢！  
3) 既然dts现在这么流行了，你又何必不用呢！设备dts中的interrupts属性都会指明中断触发type，那你就用嘛！怎么获取这个flag呢？irqd\_get\_trigger\_type()可以通过dts获取irq的触发type。所以request\_threaded\_irq()的第四个参数irqflags可以使用irqd\_get\_trigger\_type()获得。如果你的内核版本更新的话，还可以更简单，irqflags传入0即可，在request\_threaded\_irq()中会自动帮我们调用irqd\_get\_trigger\_type()获取。当然了，我也看聪明的IC厂家提供的driver，在dts中自定义一个属性表明irqflags，在driver中获取。我只能猜测driver的编写者不知道irqd\_get\_trigger\_type()接口吧！  
4) 如果中断下半部使用工作队列，请成对使用pm\_stay\_awake()和pm\_relax()。否则，谁也无法保证系统不会再一次的睡眠。

*原创文章，转发请注明出处。蜗窝科技，www.wowotech.net。*
