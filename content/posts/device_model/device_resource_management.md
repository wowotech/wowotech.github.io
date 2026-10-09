---
title: "Linux设备模型(9)_device resource management"
date: 2014-09-24T23:28:19+08:00
url: "/device_model/device_resource_management.html"
gid: "92"
emlog_type: "blog"
summary: "蜗蜗建议，每一个Linux驱动工程师，都能瞄一眼本文。 之所以用“瞄”，因此它很简单，几乎不需要花费心思就能理解。之所有这建议，是因为它非常实用，可以解答一些困惑，可以使我们的代码变得简单、简洁。先看一个例子："
author: "wowo"
category: "统一设备模型"
category_alias: "device_model"
tags: ["Linux", "设备模型", "设备资源管理", "devres"]
views: 88587
comment_count: 51
aliases:
  - "/device_model/92.html"
  - "/92.html"
---

#### 1. 前言

**蜗蜗建议，每一个Linux驱动工程师，都能瞄一眼本文。**

之所以用“瞄”，因此它很简单，几乎不需要花费心思就能理解。之所有这建议，是因为它非常实用，可以解答一些困惑，可以使我们的代码变得简单、简洁。先看一个例子：

```
   1: /* drivers/media/platform/soc_camera/mx1_camera.c, line 695 */
```

```
   2: static int __init mx1_camera_probe(struct platform_device *pdev)
```

```
   3: {
```

```
   4:     ...
```

```
   5:  
```

```
   6:     res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
```

```
   7:     irq = platform_get_irq(pdev, 0);
```

```
   8:     if (!res || (int)irq <= 0) {
```

```
   9:         err = -ENODEV;
```

```
  10:         goto exit;
```

```
  11:     }
```

```
  12:  
```

```
  13:     clk = clk_get(&pdev->dev, "csi_clk");
```

```
  14:     if (IS_ERR(clk)) {
```

```
  15:         err = PTR_ERR(clk);
```

```
  16:         goto exit;
```

```
  17:     }
```

```
  18:  
```

```
  19:     pcdev = kzalloc(sizeof(*pcdev), GFP_KERNEL);
```

```
  20:     if (!pcdev) {
```

```
  21:         dev_err(&pdev->dev, "Could not allocate pcdev\n");
```

```
  22:         err = -ENOMEM;
```

```
  23:         goto exit_put_clk;
```

```
  24:     }
```

```
  25:  
```

```
  26:     ...
```

```
  27:  
```

```
  28:     /*
```

```
  29:      * Request the regions.
```

```
  30:      */
```

```
  31:     if (!request_mem_region(res->start, resource_size(res), DRIVER_NAME)) {
```

```
  32:         err = -EBUSY;
```

```
  33:         goto exit_kfree;
```

```
  34:     }
```

```
  35:  
```

```
  36:     base = ioremap(res->start, resource_size(res));
```

```
  37:     if (!base) {
```

```
  38:         err = -ENOMEM;
```

```
  39:         goto exit_release;
```

```
  40:     }
```

```
  41:     ...
```

```
  42:  
```

```
  43:     /* request dma */
```

```
  44:     pcdev->dma_chan = imx_dma_request_by_prio(DRIVER_NAME, DMA_PRIO_HIGH);
```

```
  45:     if (pcdev->dma_chan < 0) {
```

```
  46:         dev_err(&pdev->dev, "Can't request DMA for MX1 CSI\n");
```

```
  47:         err = -EBUSY;
```

```
  48:         goto exit_iounmap;
```

```
  49:     }
```

```
  50:     ...
```

```
  51:  
```

```
  52:     /* request irq */
```

```
  53:     err = claim_fiq(&fh);
```

```
  54:     if (err) {
```

```
  55:         dev_err(&pdev->dev, "Camera interrupt register failed\n");
```

```
  56:         goto exit_free_dma;
```

```
  57:     }
```

```
  58:  
```

```
  59:     ...
```

```
  60:     err = soc_camera_host_register(&pcdev->soc_host);
```

```
  61:     if (err)
```

```
  62:         goto exit_free_irq;
```

```
  63:  
```

```
  64:     dev_info(&pdev->dev, "MX1 Camera driver loaded\n");
```

```
  65:  
```

```
  66:     return 0;
```

```
  67:  
```

```
  68: exit_free_irq:
```

```
  69:     disable_fiq(irq);
```

```
  70:     mxc_set_irq_fiq(irq, 0);
```

```
  71:     release_fiq(&fh);
```

```
  72: exit_free_dma:
```

```
  73:     imx_dma_free(pcdev->dma_chan);
```

```
  74: exit_iounmap:
```

```
  75:     iounmap(base);
```

```
  76: exit_release:
```

```
  77:     release_mem_region(res->start, resource_size(res));
```

```
  78: exit_kfree:
```

```
  79:     kfree(pcdev);
```

```
  80: exit_put_clk:
```

```
  81:     clk_put(clk);
```

```
  82: exit:
```

```
  83:     return err;
```

```
  84: }
```

相信每一个写过Linux driver的工程师，都在probe函数中遇到过上面的困惑：要顺序申请多种资源（IRQ、Clock、memory、regions、ioremap、dma、等等），只要任意一种资源申请失败，就要回滚释放之前申请的所有资源。于是函数的最后，一定会出现很多的goto标签（如上面的exit\_free\_irq、exit\_free\_dma、等等），并在申请资源出错时，小心翼翼的goto到正确的标签上，以便释放已申请资源。

正像上面代码一样，整个函数被大段的、重复的“if (condition) { err = xxx; goto xxx; }”充斥，浪费精力，容易出错，不美观。有困惑，就有改善的余地，最终，Linux设备模型借助device resource management（设备资源管理），帮我们解决了这个问题。就是：driver你只管申请就行了，不用考虑释放，我设备模型帮你释放。最终，我们的driver可以这样写：

```
   1: static int __init mx1_camera_probe(struct platform_device *pdev)
```

```
   2: {
```

```
   3:     ...
```

```
   4:  
```

```
   5:     res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
```

```
   6:     irq = platform_get_irq(pdev, 0);
```

```
   7:     if (!res || (int)irq <= 0) {
```

```
   8:         return -ENODEV;
```

```
   9:     }
```

```
  10:  
```

```
  11:     clk = devm_clk_get(&pdev->dev, "csi_clk");
```

```
  12:     if (IS_ERR(clk)) {
```

```
  13:         return PTR_ERR(clk);
```

```
  14:     }
```

```
  15:  
```

```
  16:     pcdev = devm_kzalloc(&pdev->dev, sizeof(*pcdev), GFP_KERNEL);
```

```
  17:     if (!pcdev) {
```

```
  18:         dev_err(&pdev->dev, "Could not allocate pcdev\n");
```

```
  19:         return -ENOMEM;
```

```
  20:     }
```

```
  21:  
```

```
  22:     ...
```

```
  23:  
```

```
  24:     /*
```

```
  25:      * Request the regions.
```

```
  26:      */
```

```
  27:     if (!devm_request_mem_region(&pdev->dev, res->start, resource_size(res), DRIVER_NAME)) {
```

```
  28:         return -EBUSY;
```

```
  29:     }
```

```
  30:  
```

```
  31:     base = devm_ioremap(&pdev->dev, res->start, resource_size(res));
```

```
  32:     if (!base) {
```

```
  33:         return -ENOMEM;
```

```
  34:     }
```

```
  35:     ...
```

```
  36:  
```

```
  37:     /* request dma */
```

```
  38:     pcdev->dma_chan = imx_dma_request_by_prio(DRIVER_NAME, DMA_PRIO_HIGH);
```

```
  39:     if (pcdev->dma_chan < 0) {
```

```
  40:         dev_err(&pdev->dev, "Can't request DMA for MX1 CSI\n");
```

```
  41:         return -EBUSY;
```

```
  42:     }
```

```
  43:     ...
```

```
  44:  
```

```
  45:     /* request irq */
```

```
  46:     err = claim_fiq(&fh);
```

```
  47:     if (err) {
```

```
  48:         dev_err(&pdev->dev, "Camera interrupt register failed\n");
```

```
  49:         return err;
```

```
  50:     }
```

```
  51:  
```

```
  52:     ...
```

```
  53:     err = soc_camera_host_register(&pcdev->soc_host);
```

```
  54:     if (err)
```

```
  55:         return err;
```

```
  56:  
```

```
  57:     dev_info(&pdev->dev, "MX1 Camera driver loaded\n");
```

```
  58:  
```

```
  59:     return 0;
```

```
  60: }
```

怎么做到呢？注意上面“devm\_”开头的接口，答案就在那里。不要再使用那些常规的资源申请接口，用devm\_xxx的接口代替。为了保持兼容，这些新接口和旧接口的参数保持一致，只是名字前加了“devm\_”，并多加一个struct device指针。

#### 2. devm\_xxx

下面列举一些常用的资源申请接口，它们由各个framework（如clock、regulator、gpio、等等）基于device resource management实现。使用时，直接忽略“devm\_”的前缀，后面剩下的部分，driver工程师都很熟悉。只需记住一点，driver可以只申请，不释放，设备模型会帮忙释放。不过如果为了严谨，在driver remove时，可以主动释放（也有相应的接口，这里没有列出）。

```
   1: extern void *devm_kzalloc(struct device *dev, size_t size, gfp_t gfp);
```

```
   2:  
```

```
   3: void __iomem *devm_ioremap_resource(struct device *dev, 
```

```
   4:   struct resource *res);
```

```
   5: void __iomem *devm_ioremap(struct device *dev, resource_size_t offset,
```

```
   6:   unsigned long size);
```

```
   7:  
```

```
   8: struct clk *devm_clk_get(struct device *dev, const char *id);
```

```
   9:  
```

```
  10: int devm_gpio_request(struct device *dev, unsigned gpio,
```

```
  11:   const char *label);
```

```
  12:  
```

```
  13: static inline struct pinctrl * devm_pinctrl_get_select(
```

```
  14:   struct device *dev, const char *name)
```

```
  15:  
```

```
  16: static inline struct pwm_device *devm_pwm_get(struct device *dev,
```

```
  17:   const char *consumer);
```

```
  18:  
```

```
  19: struct regulator *devm_regulator_get(struct device *dev, const char *id);
```

```
  20:  
```

```
  21: static inline int devm_request_irq(struct device *dev, unsigned int irq, 
```

```
  22:   irq_handler_t handler, unsigned long irqflags, 
```

```
  23:   const char *devname, void *dev_id);
```

```
  24:  
```

```
  25: struct reset_control *devm_reset_control_get(struct device *dev, 
```

```
  26:   const char *id);
```

#### 3. 什么是“设备资源”

一个设备能工作，需要依赖很多的外部条件，如供电、时钟等等，这些外部条件称作设备资源（device resouce）。对于现代计算机的体系结构，可能的资源包括：

> a）power，供电。
>   
> b）clock，时钟。
>   
> c）memory，内存，在kernel中一般使用kzalloc分配。
>   
> d）GPIO，用户和CPU交换简单控制、状态等信息。
>   
> e）IRQ，触发中断。
>   
> f）DMA，无CPU参与情况下进行数据传输。
>   
> g）虚拟地址空间，一般使用ioremap、request\_region等分配。
>   
> h）等等

而在Linux kernel的眼中，“资源”的定义更为广义，比如PWM、RTC、Reset，都可以抽象为资源，供driver使用。

在较早的kernel中，系统还不是特别复杂，且各个framework还没有成型，因此大多的资源都由driver自行维护。但随着系统复杂度的增加，driver之间共用资源的情况越来越多，同时电源管理的需求也越来越迫切。于是kernel就将各个resource的管理权收回，基于“device resource management”的框架，由各个framework统一管理，包括分配和回收。

#### 4. device resource management的软件框架

[![device resource management](/content/uploadfile/201409/6c5054b79c0e8e282069e5081f10de6420140925151512.gif "device resource management")](/content/uploadfile/201409/9838563badc0945a6e5e5c95013ecc7720140925151511.gif) device resource management位于“drivers/base/devres.c”中，它的实现非常简单，为什么呢？因为资源的种类有很多，表现形式也多种多样，而devres不可能一一知情，也就不能进行具体的分配和回收。因此，devres能做的（也是它的唯一功能），就是：

> 提供一种机制，将系统中某个设备的所有资源，以链表的形式，组织起来，以便在driver detach的时候，自动释放。

而更为具体的事情，如怎么抽象某一种设备，则由上层的framework负责。这些framework包括：regulator framework（管理power资源），clock framework（管理clock资源），interrupt framework（管理中断资源）、gpio framework（管理gpio资源），pwm framework（管理PWM），等等。

其它的driver，位于这些framework之上，使用它们提供的机制和接口，开发起来就非常方便了。

#### 5. 代码分析

##### 5.1 数据结构

先从struct device开始吧！该结构中有一个名称为“devres\_head”的链表头，用于保存该设备申请的所有资源，如下：

```
   1: struct device {
```

```
   2:         ...
```

```
   3:         spinlock_t              devres_lock;
```

```
   4:         struct list_head        devres_head;
```

```
   5:         ...
```

```
   6: }
```

```
   7:  
```

那资源的数据结构呢？在“drivers/base/devres.c”中，名称为struct devres，如下：

```
   1: struct devres {
```

```
   2:         struct devres_node              node;
```

```
   3:         /* -- 3 pointers */
```

```
   4:         unsigned long long              data[]; /* guarantee ull alignment */
```

```
   5: };
```

咋一看非常简单，一个struct devres\_node的变量node，一个零长度数组data，但其中有无穷奥妙，让我们继续分析。

node用于将devres组织起来，方便插入到device结构的devres\_head链表中，因此一定也有一个list\_head（见下面的entry）。另外，资源的存在形式到底是什么，device resource management并不知情，因此需要上层模块提供一个release的回调函数，用于release资源，如下：

```
   1: struct devres_node {
```

```
   2:         struct list_head                entry;
```

```
   3:         dr_release_t                    release;
```

```
   4: #ifdef CONFIG_DEBUG_DEVRES
```

```
   5:         const char                      *name;
```

```
   6:         size_t                          size;
```

```
   7: #endif
```

```
   8: };
```

抛开用于debug的变量不说，也很简单，一个entry list\_head，一个release回调函数。看不出怎么抽象资源啊！别急，奥妙都在data这个零长度数组上面呢。

注1：不知道您是否注意到，devres有关的数据结构，是在devres.c中定义的（是C文件哦！）。换句话说，是对其它模块透明的。这真是优雅的设计（尽量屏蔽细节）！

##### 5.2 一个无关话题：零长度数组

零长度数组的英文原名为Arrays of Length Zero，是GNU C的规范，主要用途是用来作为结构体的最后一个成员，然后用它来访问此结构体对象之后的一段内存（通常是动态分配的内存）。什么意思呢？

以struct devres为例，node变量的长度为3个指针的长度，而struct devres的长度也是3个指针的长度。而data只是一个标记，当有人分配了大于3个指针长度的空间并把它转换为struct devres类型的变量后，我们就可以通过data来访问多出来的memory。也就是说，有了零长度数组data，struct devres结构的长度可以不定，完全依赖于你分配的空间的大小。有什么用呢？

以本文的应用场景为例，多出来的、可通过data访问的空间，正是具体的device resource所占的空间。资源的类型不同，占用的空间的多少也不同，但devres模块的主要功能又是释放资源所占的资源。这是就是零长度数组的功能之一，因为整个memory空间是连续的，因此可以通过释devres指针，释放所有的空间，包括data所指的那片不定长度的、具体资源所用的空间。

零长度数组（data[0]），在不同的C版本中，有不同的实现方案，包括1长度数组（data[1]）和不定长度数组（data[]，本文所描述就是这一种），具体可参考GCC的规范：

[https://gcc.gnu.org/onlinedocs/gcc/Zero-Length.html](https://gcc.gnu.org/onlinedocs/gcc/Zero-Length.html "https://gcc.gnu.org/onlinedocs/gcc/Zero-Length.html")

##### 5.3 向上层framework提供的接口：devres\_alloc/devres\_free、devres\_add/devres\_remove

先看一个使用device resource management的例子（IRQ模块）：

```
   1: /* include/linux/interrupt.h */
```

```
   2: static inline int __must_check
```

```
   3: devm_request_irq(struct device *dev, unsigned int irq, irq_handler_t handler,
```

```
   4:                  unsigned long irqflags, const char *devname, void *dev_id)
```

```
   5: {
```

```
   6:         return devm_request_threaded_irq(dev, irq, handler, NULL, irqflags,
```

```
   7:                                          devname, dev_id);
```

```
   8: }
```

```
   9:  
```

```
  10:  
```

```
  11: /* kernel/irq/devres.c */
```

```
  12: int devm_request_threaded_irq(struct device *dev, unsigned int irq,
```

```
  13:                               irq_handler_t handler, irq_handler_t thread_fn,
```

```
  14:                               unsigned long irqflags, const char *devname,
```

```
  15:                               void *dev_id)
```

```
  16: {
```

```
  17:         struct irq_devres *dr;
```

```
  18:         int rc;
```

```
  19:  
```

```
  20:         dr = devres_alloc(devm_irq_release, sizeof(struct irq_devres),
```

```
  21:                           GFP_KERNEL);
```

```
  22:         if (!dr)
```

```
  23:                 return -ENOMEM;
```

```
  24:  
```

```
  25:         rc = request_threaded_irq(irq, handler, thread_fn, irqflags, devname,
```

```
  26:                                   dev_id);
```

```
  27:         if (rc) {
```

```
  28:                 devres_free(dr);
```

```
  29:                 return rc;
```

```
  30:         }
```

```
  31:  
```

```
  32:         dr->irq = irq;
```

```
  33:         dr->dev_id = dev_id;
```

```
  34:         devres_add(dev, dr);
```

```
  35:  
```

```
  36:         return 0;
```

```
  37: }
```

```
  38: EXPORT_SYMBOL(devm_request_threaded_irq);
```

```
  39:  
```

```
  40: void devm_free_irq(struct device *dev, unsigned int irq, void *dev_id)
```

```
  41: {
```

```
  42:         struct irq_devres match_data = { irq, dev_id };
```

```
  43:  
```

```
  44:         WARN_ON(devres_destroy(dev, devm_irq_release, devm_irq_match,
```

```
  45:                                &match_data));
```

```
  46:         free_irq(irq, dev_id);
```

```
  47: }
```

```
  48: EXPORT_SYMBOL(devm_free_irq);
```

前面我们提过，上层的IRQ framework，会提供两个和request\_irq/free\_irq基本兼容的接口，这两个接口的实现非常简单，就是在原有的实现之上，封装一层devres的操作，如要包括：

1）一个自定义的数据结构（struct irq\_devres），用于保存和resource有关的信息（对中断来说，就是IRQ num），如下：

```
   1: /*
```

```
   2:  * Device resource management aware IRQ request/free implementation.
```

```
   3:  */
```

```
   4: struct irq_devres {
```

```
   5:         unsigned int irq;
```

```
   6:         void *dev_id;
```

```
   7: };
```

2）一个用于release resource的回调函数（这里的release，和memory无关，例如free IRQ），如下：

```
   1: static void devm_irq_release(struct device *dev, void *res)
```

```
   2: {
```

```
   3:         struct irq_devres *this = res;
```

```
   4:  
```

```
   5:         free_irq(this->irq, this->dev_id);
```

```
   6: }
```

> 因为回调函数是由devres模块调用的，由它的参数可知，struct irq\_devres变量就是实际的“资源”，但对devres而言，它并不知道该资源的实际形态，因而是void类型指针。也只有这样，devres模块才可以统一的处理所有类型的资源。

3）以回调函数、resource的size为参数，调用devres\_alloc接口，为resource分配空间。该接口的定义如下：

```
   1: void * devres_alloc(dr_release_t release, size_t size, gfp_t gfp)
```

```
   2: {
```

```
   3:         struct devres *dr;
```

```
   4:  
```

```
   5:         dr = alloc_dr(release, size, gfp);
```

```
   6:         if (unlikely(!dr))
```

```
   7:                 return NULL;
```

```
   8:         return dr->data;
```

```
   9: }
```

调用alloc\_dr，分配一个struct devres类型的变量，并返回其中的data指针（5.2小节讲过了，data变量实际上是资源的代表）。alloc\_dr的定义如下：

```
   1: static __always_inline struct devres * alloc_dr(dr_release_t release,
```

```
   2:                                                 size_t size, gfp_t gfp)
```

```
   3: {
```

```
   4:         size_t tot_size = sizeof(struct devres) + size;
```

```
   5:         struct devres *dr;
```

```
   6:  
```

```
   7:         dr = kmalloc_track_caller(tot_size, gfp);
```

```
   8:         if (unlikely(!dr))
```

```
   9:                 return NULL;
```

```
  10:  
```

```
  11:         memset(dr, 0, tot_size);
```

```
  12:         INIT_LIST_HEAD(&dr->node.entry);
```

```
  13:         dr->node.release = release;
```

```
  14:         return dr;
```

```
  15: }
```

看第一句就可以了，在资源size之前，加一个struct devres的size，就是total分配的空间。除去struct devres的，就是资源的（由data指针访问）。之后是初始化struct devres变量的node。

4）调用原来的中断注册接口（这里是request\_threaded\_irq），注册中断。该步骤和device resource management无关。

5）注册成功后，以设备指针（dev）和资源指针（dr）为参数，调用devres\_add，将资源添加到设备的资源链表头（devres\_head）中，该接口定义如下：

```
   1: void devres_add(struct device *dev, void *res)
```

```
   2: {
```

```
   3:         struct devres *dr = container_of(res, struct devres, data);
```

```
   4:         unsigned long flags;
```

```
   5:  
```

```
   6:         spin_lock_irqsave(&dev->devres_lock, flags);
```

```
   7:         add_dr(dev, &dr->node);
```

```
   8:         spin_unlock_irqrestore(&dev->devres_lock, flags);
```

```
   9: }
```

从资源指针中，取出完整的struct devres指针，调用add\_dr接口。add\_dr也很简单，把struct devres指针挂到设备的devres\_head中即可：

```
   1: static void add_dr(struct device *dev, struct devres_node *node)
```

```
   2: {
```

```
   3:         devres_log(dev, node, "ADD");
```

```
   4:         BUG_ON(!list_empty(&node->entry));
```

```
   5:         list_add_tail(&node->entry, &dev->devres_head);
```

```
   6: }
```

6）如果失败，可以通过devres\_free接口释放资源占用的空间，devm\_free\_irq接口中，会调用devres\_destroy接口，将devres从devres\_head中移除，并释放资源。这里就不详细描述了。

##### 5.4 向设备模型提供的接口：devres\_release\_all

这里是重点，用于自动释放资源。

先回忆一下设备模型中probe的流程（可参考“[Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)”），devres\_release\_all接口被调用的时机有两个：

1）probe失败时，调用过程为（就不详细的贴代码了）：

\_\_driver\_attach/\_\_device\_attach-->driver\_probe\_device—>really\_probe，really\_probe调用driver或者bus的probe接口，如果失败（返回值非零，可参考本文开头的例子），则会调用devres\_release\_all。

2）deriver dettach时（就是driver remove时）

driver\_detach/bus\_remove\_device-->\_\_device\_release\_driver-->devres\_release\_all

devres\_release\_all的实现如下：

```
   1: int devres_release_all(struct device *dev)
```

```
   2: {
```

```
   3:         unsigned long flags;
```

```
   4:  
```

```
   5:         /* Looks like an uninitialized device structure */
```

```
   6:         if (WARN_ON(dev->devres_head.next == NULL))
```

```
   7:                 return -ENODEV;
```

```
   8:         spin_lock_irqsave(&dev->devres_lock, flags);
```

```
   9:         return release_nodes(dev, dev->devres_head.next, &dev->devres_head,
```

```
  10:                              flags);
```

```
  11: }
```

以设备指针为参数，直接调用release\_nodes：

```
   1: static int release_nodes(struct device *dev, struct list_head *first,
```

```
   2:                          struct list_head *end, unsigned long flags)
```

```
   3:         __releases(&dev->devres_lock)
```

```
   4: {
```

```
   5:         LIST_HEAD(todo);
```

```
   6:         int cnt;
```

```
   7:         struct devres *dr, *tmp;
```

```
   8:  
```

```
   9:         cnt = remove_nodes(dev, first, end, &todo);
```

```
  10:  
```

```
  11:         spin_unlock_irqrestore(&dev->devres_lock, flags);
```

```
  12:  
```

```
  13:         /* Release.  Note that both devres and devres_group are
```

```
  14:          * handled as devres in the following loop.  This is safe.
```

```
  15:          */
```

```
  16:         list_for_each_entry_safe_reverse(dr, tmp, &todo, node.entry) {
```

```
  17:                 devres_log(dev, &dr->node, "REL");
```

```
  18:                 dr->node.release(dev, dr->data);
```

```
  19:                 kfree(dr);
```

```
  20:         }
```

```
  21:  
```

```
  22:         return cnt;
```

```
  23: }
```

release\_nodes会先调用remove\_nodes，将设备所有的struct devres指针从设备的devres\_head中移除。然后，调用所有资源的release回调函数（如5.3小节描述的devm\_irq\_release），回调函数会回收具体的资源（如free\_irq)。最后，调用free，释放devres以及资源所占的空间。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/device_model/device_resource_management.html)。
