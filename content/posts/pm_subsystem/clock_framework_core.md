---
title: "Linux common clock framework(3)_实现逻辑分析"
date: 2014-11-24T22:31:28+08:00
url: "/pm_subsystem/clock_framework_core.html"
gid: "113"
emlog_type: "blog"
summary: "前面两篇clock framework的分析文章，分别从 clock consumer 和 clock provider 的角度，介绍了Linux kernel怎么管理系统的clock资源，以及device driver怎么使用clock资源。本文将深入到clock framework的内部，分析相关的实现逻辑。 注：本文使用的kernel版本为linux-3.10.29。虽然最新版本的kerne"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "clock", "实现"]
views: 37383
comment_count: 22
aliases:
  - "/pm_subsystem/113.html"
  - "/113.html"
---

#### 1. 前言

前面两篇clock framework的分析文章，分别从[clock consumer](/pm_subsystem/clk_overview.html)和[clock provider](/pm_subsystem/clock_provider.html)的角度，介绍了Linux kernel怎么管理系统的clock资源，以及device driver怎么使用clock资源。本文将深入到clock framework的内部，分析相关的实现逻辑。

注：本文使用的kernel版本为linux-3.10.29。虽然最新版本的kernel增加了一些内容，但主要逻辑没有改变，就不紧跟kernel的步伐了。

#### 2. struct clk结构

到目前为止，我们还没有仔细介绍过struct clk这个代表了一个clock的数据结构呢。对consumer和provider来说，可以不关心，但对内部实现逻辑来说，就不得不提了：

```
   1: /* include/linux/clk-private.h */
```

```
   2: struct clk {
```

```
   3:         const char              *name;
```

```
   4:         const struct clk_ops    *ops;
```

```
   5:         struct clk_hw           *hw;
```

```
   6:         struct clk              *parent;
```

```
   7:         const char              **parent_names;
```

```
   8:         struct clk              **parents;
```

```
   9:         u8                      num_parents;
```

```
  10:         unsigned long           rate;
```

```
  11:         unsigned long           new_rate;
```

```
  12:         unsigned long           flags;
```

```
  13:         unsigned int            enable_count;
```

```
  14:         unsigned int            prepare_count;
```

```
  15:         struct hlist_head       children;
```

```
  16:         struct hlist_node       child_node;
```

```
  17:         unsigned int            notifier_count;
```

```
  18: #ifdef CONFIG_COMMON_CLK_DEBUG
```

```
  19:         struct dentry           *dentry;
```

```
  20: #endif
```

```
  21: };
```

> name, ops, hw, parents\_name, num\_parents, flags, 可参考“[Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”中的相关描述；
>
> parent，保存了该clock当前的parent clock的struct clk指针；
>
> parents，一个指针数组，保存了所有可能的parent clock的struct clk指针；
>
> rate，当前的clock rate；
>
> new\_rate,新设置的clock rate，之所要保存在这里，是因为set rate过程中有一些中间计算，后面再详解；
>
> enable\_count, prepare\_count，该clock被enable和prepare的次数，用于确保enable/disable以及prepare/unprepare的成对调用；
>
> children，该clock的children clocks（孩儿们），以链表的形式组织；
>
> child\_node，一个list node，自己作为child时，挂到parent的children list时使用；
>
> notifier\_count，记录注册到notifier的个数。

#### 3. clock regitser/unregister

在“[Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”中已经讲过，clock provider需要将系统的clock以tree的形式组织起来，分门别类，并在系统初始化时，通过provider的初始化接口，或者clock framework core的DTS接口，将所有的clock注册到kernel。

clock的注册，统一由clk\_regitser接口实现，但基于该接口，kernel也提供了其它更为便利注册接口，下面将会一一描述。

##### 3.1 clk\_regitser

clk\_register是所有register接口的共同实现，负责将clock注册到kernel，并返回代表该clock的struct clk指针。分析该接口之前，我们先看一下下面的内容：

```
   1: 1 F   f    clk_register      .\arch\arm\mach-at91\clock.c
```

```
   2:              int __init clk_register(struct clk *clk)
```

```
   3: 2 F   v    clk_register      .\arch\arm\mach-davinci\clock.c
```

```
   4:              EXPORT_SYMBOL(clk_register);
```

```
   5: 3 F   f    clk_register      .\arch\arm\mach-davinci\clock.c
```

```
   6:              int clk_register(struct clk *clk)
```

```
   7: 4 F   v    clk_register      .\arch\arm\mach-omap1\clock.c
```

```
   8:              EXPORT_SYMBOL(clk_register);
```

```
   9: 5 F   f    clk_register      .\arch\arm\mach-omap1\clock.c
```

```
  10:              int clk_register(struct clk *clk)
```

```
  11: 6 F   v    clk_register      .\arch\c6x\platforms\pll.c
```

```
  12:              EXPORT_SYMBOL(clk_register);
```

```
  13: 7 F   f    clk_register      .\arch\c6x\platforms\pll.c
```

```
  14:              int clk_register(struct clk *clk)
```

```
  15: 8 F   v    clk_register      .\arch\unicore32\kernel\clock.c
```

```
  16:              EXPORT_SYMBOL(clk_register);
```

```
  17: 9 F   f    clk_register      .\arch\unicore32\kernel\clock.c
```

```
  18:              int clk_register(struct clk *clk)
```

```
  19: 0 F   v    clk_register      .\drivers\clk\clk.c
```

```
  20:              EXPORT_SYMBOL_GPL(clk_register);
```

```
  21: 1 F   f    clk_register      .\drivers\clk\clk.c
```

```
  22:              struct clk *clk_register(struct device *dev, struct clk_hw *hw)
```

```
  23: 2 F   v    clk_register      .\drivers\sh\clk\core.c
```

```
  24:              EXPORT_SYMBOL_GPL(clk_register);
```

```
  25: 3 F   f    clk_register      .\drivers\sh\clk\core.c
```

```
  26:              int clk_register(struct clk *clk)
```

> 上面是kernel中clk\_register接口可能的实现位置，由此可以看出，clk\_register在“include/linux/clk-provider.h”中声明，却可能在不同的C文件中实现。其它clock API也类似。这说明了什么？
>
> 这恰恰呼应了“Linux common clock framework”中“common”一词。
>
> 在旧的kernel中，clock framework只是规定了一系列的API声明，具体API的实现，由各个machine代码完成。这就导致每个machine目录下，都有一个类似clock.c的文件，以比较相似的逻辑，实现clock provider的功能。显然，这里面有很多冗余代码。
>
> 后来，kernel将这些公共代码，以clock provider的形式（上面drivers/clk/clk.c文件）抽象出来，就成了我们所说的common clock framework。
>
> 后面所有的描述，都会以common clock framework的核心代码为基础，其它的，就不再涉及了。

下面是clk\_register的实现：

```
   1: /**
```

```
   2:  * clk_register - allocate a new clock, register it and return an opaque cookie
```

```
   3:  * @dev: device that is registering this clock
```

```
   4:  * @hw: link to hardware-specific clock data
```

```
   5:  *
```

```
   6:  * clk_register is the primary interface for populating the clock tree with new
```

```
   7:  * clock nodes.  It returns a pointer to the newly allocated struct clk which
```

```
   8:  * cannot be dereferenced by driver code but may be used in conjuction with the
```

```
   9:  * rest of the clock API.  In the event of an error clk_register will return an
```

```
  10:  * error code; drivers must test for an error code after calling clk_register.
```

```
  11:  */
```

```
  12: struct clk *clk_register(struct device *dev, struct clk_hw *hw)
```

```
  13: {
```

```
  14:     int i, ret;
```

```
  15:     struct clk *clk;
```

```
  16:  
```

```
  17:     clk = kzalloc(sizeof(*clk), GFP_KERNEL);
```

```
  18:     if (!clk) {
```

```
  19:         pr_err("%s: could not allocate clk\n", __func__);
```

```
  20:         ret = -ENOMEM;
```

```
  21:         goto fail_out;
```

```
  22:     }
```

```
  23:  
```

```
  24:     clk->name = kstrdup(hw->init->name, GFP_KERNEL);
```

```
  25:     if (!clk->name) {
```

```
  26:         pr_err("%s: could not allocate clk->name\n", __func__);
```

```
  27:         ret = -ENOMEM;
```

```
  28:         goto fail_name;
```

```
  29:     }
```

```
  30:     clk->ops = hw->init->ops;
```

```
  31:     if (dev && dev->driver)
```

```
  32:         clk->owner = dev->driver->owner;
```

```
  33:     clk->hw = hw;
```

```
  34:     clk->flags = hw->init->flags;
```

```
  35:     clk->num_parents = hw->init->num_parents;
```

```
  36:     hw->clk = clk;
```

```
  37:  
```

```
  38:     /* allocate local copy in case parent_names is __initdata */
```

```
  39:     clk->parent_names = kcalloc(clk->num_parents, sizeof(char *),
```

```
  40:                     GFP_KERNEL);
```

```
  41:  
```

```
  42:     if (!clk->parent_names) {
```

```
  43:         pr_err("%s: could not allocate clk->parent_names\n", __func__);
```

```
  44:         ret = -ENOMEM;
```

```
  45:         goto fail_parent_names;
```

```
  46:     }
```

```
  47:  
```

```
  48:  
```

```
  49:     /* copy each string name in case parent_names is __initdata */
```

```
  50:     for (i = 0; i < clk->num_parents; i++) {
```

```
  51:         clk->parent_names[i] = kstrdup(hw->init->parent_names[i],
```

```
  52:                         GFP_KERNEL);
```

```
  53:         if (!clk->parent_names[i]) {
```

```
  54:             pr_err("%s: could not copy parent_names\n", __func__);
```

```
  55:             ret = -ENOMEM;
```

```
  56:             goto fail_parent_names_copy;
```

```
  57:         }
```

```
  58:     }
```

```
  59:  
```

```
  60:     ret = __clk_init(dev, clk);
```

```
  61:     if (!ret)
```

```
  62:         return clk;
```

```
  63:  
```

```
  64: fail_parent_names_copy:
```

```
  65:     while (--i >= 0)
```

```
  66:         kfree(clk->parent_names[i]);
```

```
  67:     kfree(clk->parent_names);
```

```
  68: fail_parent_names:
```

```
  69:     kfree(clk->name);
```

```
  70: fail_name:
```

```
  71:     kfree(clk);
```

```
  72: fail_out:
```

```
  73:     return ERR_PTR(ret);
```

```
  74: }
```

```
  75: EXPORT_SYMBOL_GPL(clk_register);
```

> 该接口接受一个struct clk\_hw指针，该指针包含了将要注册的clock的信息（具体可参考“[Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”），在内部分配一个struct clk变量后，将clock信息保存在变量中，并返回给调用者。实现逻辑如下：
>
> 分配struct clk空间；
>
> 根据struct clk\_hw指针提供的信息，初始化clk的name、ops、hw、flags、num\_parents、parents\_names等变量；
>
> 调用内部接口\_\_clk\_init，执行后续的初始化操作。这个接口包含了clk\_regitser的主要逻辑，具体如下。

```
   1: /**
```

```
   2:  * __clk_init - initialize the data structures in a struct clk
```

```
   3:  * @dev:    device initializing this clk, placeholder for now
```

```
   4:  * @clk:    clk being initialized
```

```
   5:  *
```

```
   6:  * Initializes the lists in struct clk, queries the hardware for the
```

```
   7:  * parent and rate and sets them both.
```

```
   8:  */
```

```
   9: int __clk_init(struct device *dev, struct clk *clk)
```

```
  10: {
```

```
  11:     int i, ret = 0;
```

```
  12:     struct clk *orphan;
```

```
  13:     struct hlist_node *tmp2;
```

```
  14:  
```

```
  15:     if (!clk)
```

```
  16:         return -EINVAL;
```

```
  17:  
```

```
  18:     clk_prepare_lock();
```

```
  19:  
```

```
  20:     /* check to see if a clock with this name is already registered */
```

```
  21:     if (__clk_lookup(clk->name)) {
```

```
  22:         pr_debug("%s: clk %s already initialized\n",
```

```
  23:                 __func__, clk->name);
```

```
  24:         ret = -EEXIST;
```

```
  25:         goto out;
```

```
  26:     }
```

```
  27:  
```

```
  28:     /* check that clk_ops are sane.  See Documentation/clk.txt */
```

```
  29:     if (clk->ops->set_rate &&
```

```
  30:             !(clk->ops->round_rate && clk->ops->recalc_rate)) {
```

```
  31:         pr_warning("%s: %s must implement .round_rate & .recalc_rate\n",
```

```
  32:                 __func__, clk->name);
```

```
  33:         ret = -EINVAL;
```

```
  34:         goto out;
```

```
  35:     }
```

```
  36:  
```

```
  37:     if (clk->ops->set_parent && !clk->ops->get_parent) {
```

```
  38:         pr_warning("%s: %s must implement .get_parent & .set_parent\n",
```

```
  39:                 __func__, clk->name);
```

```
  40:         ret = -EINVAL;
```

```
  41:         goto out;
```

```
  42:     }
```

```
  43:  
```

```
  44:     /* throw a WARN if any entries in parent_names are NULL */
```

```
  45:     for (i = 0; i < clk->num_parents; i++)
```

```
  46:         WARN(!clk->parent_names[i],
```

```
  47:                 "%s: invalid NULL in %s's .parent_names\n",
```

```
  48:                 __func__, clk->name);
```

```
  49:  
```

```
  50:     /*
```

```
  51:      * Allocate an array of struct clk *'s to avoid unnecessary string
```

```
  52:      * look-ups of clk's possible parents.  This can fail for clocks passed
```

```
  53:      * in to clk_init during early boot; thus any access to clk->parents[]
```

```
  54:      * must always check for a NULL pointer and try to populate it if
```

```
  55:      * necessary.
```

```
  56:      *
```

```
  57:      * If clk->parents is not NULL we skip this entire block.  This allows
```

```
  58:      * for clock drivers to statically initialize clk->parents.
```

```
  59:      */
```

```
  60:     if (clk->num_parents > 1 && !clk->parents) {
```

```
  61:         clk->parents = kzalloc((sizeof(struct clk*) * clk->num_parents),
```

```
  62:                 GFP_KERNEL);
```

```
  63:         /*
```

```
  64:          * __clk_lookup returns NULL for parents that have not been
```

```
  65:          * clk_init'd; thus any access to clk->parents[] must check
```

```
  66:          * for a NULL pointer.  We can always perform lazy lookups for
```

```
  67:          * missing parents later on.
```

```
  68:          */
```

```
  69:         if (clk->parents)
```

```
  70:             for (i = 0; i < clk->num_parents; i++)
```

```
  71:                 clk->parents[i] =
```

```
  72:                     __clk_lookup(clk->parent_names[i]);
```

```
  73:     }
```

```
  74:  
```

```
  75:     clk->parent = __clk_init_parent(clk);
```

```
  76:  
```

```
  77:     /*
```

```
  78:      * Populate clk->parent if parent has already been __clk_init'd.  If
```

```
  79:      * parent has not yet been __clk_init'd then place clk in the orphan
```

```
  80:      * list.  If clk has set the CLK_IS_ROOT flag then place it in the root
```

```
  81:      * clk list.
```

```
  82:      *
```

```
  83:      * Every time a new clk is clk_init'd then we walk the list of orphan
```

```
  84:      * clocks and re-parent any that are children of the clock currently
```

```
  85:      * being clk_init'd.
```

```
  86:      */
```

```
  87:     if (clk->parent)
```

```
  88:         hlist_add_head(&clk->child_node,
```

```
  89:                 &clk->parent->children);
```

```
  90:     else if (clk->flags & CLK_IS_ROOT)
```

```
  91:         hlist_add_head(&clk->child_node, &clk_root_list);
```

```
  92:     else
```

```
  93:         hlist_add_head(&clk->child_node, &clk_orphan_list);
```

```
  94:  
```

```
  95:     /*
```

```
  96:      * Set clk's rate.  The preferred method is to use .recalc_rate.  For
```

```
  97:      * simple clocks and lazy developers the default fallback is to use the
```

```
  98:      * parent's rate.  If a clock doesn't have a parent (or is orphaned)
```

```
  99:      * then rate is set to zero.
```

```
 100:      */
```

```
 101:     if (clk->ops->recalc_rate)
```

```
 102:         clk->rate = clk->ops->recalc_rate(clk->hw,
```

```
 103:                 __clk_get_rate(clk->parent));
```

```
 104:     else if (clk->parent)
```

```
 105:         clk->rate = clk->parent->rate;
```

```
 106:     else
```

```
 107:         clk->rate = 0;
```

```
 108:  
```

```
 109:     /*
```

```
 110:      * walk the list of orphan clocks and reparent any that are children of
```

```
 111:      * this clock
```

```
 112:      */
```

```
 113:     hlist_for_each_entry_safe(orphan, tmp2, &clk_orphan_list, child_node) {
```

```
 114:         if (orphan->ops->get_parent) {
```

```
 115:             i = orphan->ops->get_parent(orphan->hw);
```

```
 116:             if (!strcmp(clk->name, orphan->parent_names[i]))
```

```
 117:                 __clk_reparent(orphan, clk);
```

```
 118:             continue;
```

```
 119:         }
```

```
 120:  
```

```
 121:         for (i = 0; i < orphan->num_parents; i++)
```

```
 122:             if (!strcmp(clk->name, orphan->parent_names[i])) {
```

```
 123:                 __clk_reparent(orphan, clk);
```

```
 124:                 break;
```

```
 125:             }
```

```
 126:      }
```

```
 127:  
```

```
 128:     /*
```

```
 129:      * optional platform-specific magic
```

```
 130:      *
```

```
 131:      * The .init callback is not used by any of the basic clock types, but
```

```
 132:      * exists for weird hardware that must perform initialization magic.
```

```
 133:      * Please consider other ways of solving initialization problems before
```

```
 134:      * using this callback, as it's use is discouraged.
```

```
 135:      */
```

```
 136:     if (clk->ops->init)
```

```
 137:         clk->ops->init(clk->hw);
```

```
 138:  
```

```
 139:     clk_debug_register(clk);
```

```
 140:  
```

```
 141: out:
```

```
 142:     clk_prepare_unlock();
```

```
 143:  
```

```
 144:     return ret;
```

```
 145: }
```

> \_\_clk\_init接口的实现相当繁琐，做的事情包括：
>
> 20~26行，以clock name为参数，调用\_\_clk\_lookup接口，查找是否已有相同name的clock注册，如果有，则返回错误。由此可以看出，clock framework以name唯一识别一个clock，因此不能有同名的clock存在；
>
> 28~42行，检查clk ops的完整性，例如：如果提供了set\_rate接口，就必须提供round\_rate和recalc\_rate接口；如果提供了set\_parent，就必须提供get\_parent。这些逻辑背后的含义，会在后面相应的地方详细描述；
>
> 50~73行，分配一个struct clk \*类型的数组，缓存该clock的parents clock。具体方法是根据parents\_name，查找相应的struct clk指针；
>
> 75行，获取当前的parent clock，并将其保存在parent指针中。具体可参考下面“说明2”；
>
> 77~93行，根据该clock的特性，将它添加到clk\_root\_list、clk\_orphan\_list或者parent->children三个链表中的一个，具体请参考下面“说明1”；
>
> 95~107行，计算clock的初始rate，具体请参考下面“说明3”；
>
> 109~126行，尝试reparent当前所有的孤儿（orphan）clock，具体请参考下面“说明4”；
>
> 128~137行，如果clock ops提供了init接口，执行之（由注释可知，kernel不建议提供init接口）。

上面的clock init流程，有下面4点补充说明：

说明1：clock的管理和查询

> clock framework有2条全局的链表：clk\_root\_list和clk\_orphan\_list。所有设置了CLK\_IS\_ROOT属性的clock都会挂在clk\_root\_list中。其它clock，如果有valid的parent ，则会挂到parent的“children”链表中，如果没有valid的parent，则会挂到clk\_orphan\_list中。
>
> 查询时（\_\_clk\_lookup接口做的事情），依次搜索：clk\_root\_list-->root\_clk-->children-->child's children，clk\_orphan\_list-->orphan\_clk-->children-->child's children，即可。

说明2：当前parent clock的选择（\_\_clk\_init\_parent）

> 对于没有parent，或者只有1个parent 的clock来说，比较简单，设置为NULL，或者根据parent name获得parent的struct clk指针接。
>
> 对于有多个parent的clock，就必须提供.get\_parent ops，该ops要根据当前硬件的配置情况，例如寄存器值，返回当前所有使用的parent的index（即第几个parent）。然后根据index，取出对应parent clock的struct clk指针，作为当前的parent。

说明3：clock的初始rate计算

> 对于提供.recalc\_rate ops的clock来说，优先使用该ops获取初始的rate。如果没有提供，退而求其次，直接使用parent clock的rate。最后，如果该clock没有parent，则初始的rate只能选择为0。
>
> .recalc\_rate ops的功能，是以parent clock的rate为输入参数，根据当前硬件的配置情况，如寄存器值，计算获得自身的rate值。

说明4：orphan clocks的reparent

> 有些情况下，child clock会先于parent clock注册，此时该child就会成为orphan clock，被收养在clk\_orphan\_list中。
>
> 而每当新的clock注册时，kernel都会检查这个clock是否是某个orphan的parent，如果是，就把这个orphan从clk\_orphan\_list中移除，放到新注册的clock的怀抱。这就是reparent的功能，它的处理逻辑是：
>
> a） 遍历orphan list，如果orphan提供了.get\_parent ops，则通过该ops得到当前parent的index，并从parent\_names中取出该parent的name，然后和新注册的clock name比较，如果相同，呵呵，找到parent了，执行\_\_clk\_reparent，进行后续的操作。
>
> b） 如果没有提供.get\_parent ops，只能遍历自己的parent\_names，检查是否有和新注册clock匹配的，如果有，执行\_\_clk\_reparent，进行后续的操作。
>
> c） \_\_clk\_reparent会把这个orphan从clk\_orphan\_list中移除，并挂到新注册的clock上。然后调用\_\_clk\_recalc\_rates，重新计算自己以及自己所有children的rate。计算过程和上面的clock rate设置类似。

##### 3.2 clk\_unregister/devm\_clk\_register/devm\_clk\_unregister

clock的regitser和init，几乎占了clock framework大部分的实现逻辑。clk\_unregister是regitser接口的反操作，不过当前没有实现（不需要）。而devm\_clk\_register/devm\_clk\_unregister则是clk\_register/clk\_unregister的device resource manager版本。

##### 3.3 fixed rate clock的注册

[“Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”中已经对fixed rate clock有过详细的介绍，这种类型的clock有两种注册方式，通过API注册和通过DTS注册，具体的实现位于“drivers/clk/clk-fixed-rate.c”中，介绍如下。

1）通过API注册

```
   1: struct clk *clk_register_fixed_rate(struct device *dev, const char *name,
```

```
   2:                 const char *parent_name, unsigned long flags,
```

```
   3:                 unsigned long fixed_rate)
```

```
   4: {
```

```
   5:         struct clk_fixed_rate *fixed;
```

```
   6:         struct clk *clk;
```

```
   7:         struct clk_init_data init;
```

```
   8:  
```

```
   9:         /* allocate fixed-rate clock */
```

```
  10:         fixed = kzalloc(sizeof(struct clk_fixed_rate), GFP_KERNEL);
```

```
  11:         if (!fixed) {
```

```
  12:                 pr_err("%s: could not allocate fixed clk\n", __func__);
```

```
  13:                 return ERR_PTR(-ENOMEM);
```

```
  14:         }
```

```
  15:  
```

```
  16:         init.name = name;
```

```
  17:         init.ops = &clk_fixed_rate_ops;
```

```
  18:         init.flags = flags | CLK_IS_BASIC;
```

```
  19:         init.parent_names = (parent_name ? &parent_name: NULL);
```

```
  20:         init.num_parents = (parent_name ? 1 : 0);
```

```
  21:  
```

```
  22:         /* struct clk_fixed_rate assignments */
```

```
  23:         fixed->fixed_rate = fixed_rate;
```

```
  24:         fixed->hw.init = &init;
```

```
  25:  
```

```
  26:         /* register the clock */
```

```
  27:         clk = clk_register(dev, &fixed->hw);
```

```
  28:  
```

```
  29:         if (IS_ERR(clk))
```

```
  30:                 kfree(fixed);
```

```
  31:  
```

```
  32:         return clk;
```

```
  33: }
```

> clk\_register\_fixed\_rate API用于注册fixed rate clock，它接收传入的name、parent\_name、flags、fixed\_rate等参数，并转换为struct clk\_hw结构，最终调用clk\_register接口，注册clock。大致的逻辑如下：
>
> 16~20行，定义一个struct clk\_init\_data类型的变量（init），并根据传入的参数以及fixed rate clock的特性，初始化该变量；
>
> 22~30行，分配一个私有的数据结构（struct clk\_fixed\_rate），并将init的指针保存在其中，最后调用clk\_regitser注册该clock。

说明1：struct clk\_init\_data类型的变量

struct clk\_init\_data类型的变量（init），是一个局部变量，传递给clk\_regitser使用时，用的是它的指针，说明了什么？说明该变量不会再后面使用了。再回忆一下clk\_regitser的实现逻辑，会把所有的信息copy一遍，这里就好理解了。后面其它类型的clock注册时，道理相同。

说明2：fixed rate clock的实现思路

私有数据结构的定义如下：

```
   1: struct clk_fixed_rate {
```

```
   2:         struct          clk_hw hw;
```

```
   3:         unsigned long   fixed_rate;
```

```
   4:         u8              flags;
```

```
   5: };
```

包含一个struct clk\_hw变量，用于clk\_regitser。另外两个变量，则为该类型clock特有的属性。私有数据结构变量（fixed）是通过kzalloc分配的，说明后续还需要使用。那怎么用呢？

由clk\_regitser的实现可知，fixed rate clock注册时hw);>，把fixed指针中hw变量的地址保存在了struct clk指针中了。因此，在任何时候，通过struct clk指针（clock的代表），就可以找到所对应clock的struct clk\_hw指针，从而可以找到相应的私有变量（fixed）的指针以及其中的私有数据。

基于此，fixed rate ops的实现就顺利成章了：

```
   1: #define to_clk_fixed_rate(_hw) container_of(_hw, struct clk_fixed_rate, hw)
```

```
   2:  
```

```
   3: static unsigned long clk_fixed_rate_recalc_rate(struct clk_hw *hw,
```

```
   4:                 unsigned long parent_rate)
```

```
   5: {
```

```
   6:         return to_clk_fixed_rate(hw)->fixed_rate;
```

```
   7: }
```

```
   8:  
```

```
   9: const struct clk_ops clk_fixed_rate_ops = {
```

```
  10:         .recalc_rate = clk_fixed_rate_recalc_rate,
```

```
  11: };
```

```
  12: EXPORT_SYMBOL_GPL(clk_fixed_rate_ops);
```

2）通过DTS注册

fixed rate clock是非常简单的一种clock，因而可以直接通过DTS的形式注册，clock framework负责解析DTS，并调用API注册clock，如下：

```
   1: #ifdef CONFIG_OF
```

```
   2: /**
```

```
   3:  * of_fixed_clk_setup() - Setup function for simple fixed rate clock
```

```
   4:  */
```

```
   5: void of_fixed_clk_setup(struct device_node *node)
```

```
   6: {
```

```
   7:         struct clk *clk;
```

```
   8:         const char *clk_name = node->name;
```

```
   9:         u32 rate;
```

```
  10:  
```

```
  11:         if (of_property_read_u32(node, "clock-frequency", &rate))
```

```
  12:                 return;
```

```
  13:  
```

```
  14:         of_property_read_string(node, "clock-output-names", &clk_name);
```

```
  15:  
```

```
  16:         clk = clk_register_fixed_rate(NULL, clk_name, NULL, CLK_IS_ROOT, rate);
```

```
  17:         if (!IS_ERR(clk))
```

```
  18:                 of_clk_add_provider(node, of_clk_src_simple_get, clk);
```

```
  19: }
```

```
  20: EXPORT_SYMBOL_GPL(of_fixed_clk_setup);
```

```
  21: CLK_OF_DECLARE(fixed_clk, "fixed-clock", of_fixed_clk_setup);
```

```
  22: #endif
```

> 首先看一下CLK\_OF\_DECLARE宏，它的定义位于“include/linux/clk-provider.h”中，负责在指定的section中（以\_\_clk\_of\_table开始的位置），定义struct of\_device\_id类型的变量，并由of\_clk\_init接口解析、匹配，如果匹配成功，则执行相应的回调函数（这里为of\_fixed\_clk\_setup）；
>
> 初始化的时候，device tree负责读取DTS，并和这些变量的名字（这里为"fixed-clock"）匹配，如果匹配成功，则执行相应的回调函数（这里为of\_fixed\_clk\_setup）；
>
> of\_fixed\_clk\_setup会解析两个DTS字段"clock-frequency"和"clock-output-names"，然后调用clk\_register\_fixed\_rate，注册clock。注意，注册时的flags为CLK\_IS\_ROOT，说明目前只支持ROOT类型的clock通过DTS注册；
>
> 最后，调用of\_clk\_add\_provider接口，将该clock添加到provider list中，方便后续的查找使用。该接口会在后面再详细介绍。

of\_clk\_init负责从DTS中扫描并初始化clock provider，如下：

```
   1: /* drivers/clk/clk.c */
```

```
   2: /**
```

```
   3:  * of_clk_init() - Scan and init clock providers from the DT
```

```
   4:  * @matches: array of compatible values and init functions for providers.
```

```
   5:  *
```

```
   6:  * This function scans the device tree for matching clock providers and
```

```
   7:  * calls their initialization functions
```

```
   8:  */
```

```
   9: void __init of_clk_init(const struct of_device_id *matches)
```

```
  10: {
```

```
  11:         struct device_node *np;
```

```
  12:  
```

```
  13:         if (!matches)
```

```
  14:                 matches = __clk_of_table;
```

```
  15:  
```

```
  16:         for_each_matching_node(np, matches) {
```

```
  17:                 const struct of_device_id *match = of_match_node(matches, np);
```

```
  18:                 of_clk_init_cb_t clk_init_cb = match->data;
```

```
  19:                 clk_init_cb(np);
```

```
  20:         }
```

```
  21: }
```

> 该接口有一个输入参数，用于指定需要扫描的OF id，如果留空，则会扫描\_\_clk\_of\_table，就是通过CLK\_OF\_DECLARE宏指定的fixed rate等类型的clock。
>
> 在最新的kernel中，会在初始化代码（time\_init）中以NULL为参数调用一次of\_clk\_init，以便自动匹配并初始化DTS中的描述的类似fixed rate的clock。

注2：这里使用大量篇幅描述一个简单的fixed rate clock的注册方式，主要目的是给大家介绍一种通用的实现方式，或者说通用思路。后面其它类型的clock，包括我们自定义的类型，实现方法都是一样的。这里就不罗嗦了，大家看代码就可以了。

##### 3.4 gate、devider、mux、fixed factor、composite以及自定义类型clock的注册

和fixed rate类似，不再一一说明。

#### 4. 通用API的实现

##### 4.1 clock get

clock get是通过clock名称获取struct clk指针的过程，由clk\_get、devm\_clk\_get、clk\_get\_sys、of\_clk\_get、of\_clk\_get\_by\_name、of\_clk\_get\_from\_provider等接口负责实现，这里以clk\_get为例，分析其实现过程（位于drivers/clk/clkdev.c中）。

1）clk\_get

```
   1: struct clk *clk_get(struct device *dev, const char *con_id)
```

```
   2: {
```

```
   3:         const char *dev_id = dev ? dev_name(dev) : NULL;
```

```
   4:         struct clk *clk;
```

```
   5:  
```

```
   6:         if (dev) {
```

```
   7:                 clk = of_clk_get_by_name(dev->of_node, con_id);
```

```
   8:                 if (!IS_ERR(clk) && __clk_get(clk))
```

```
   9:                         return clk;
```

```
  10:         }
```

```
  11:  
```

```
  12:         return clk_get_sys(dev_id, con_id);
```

```
  13: }
```

> 如果提供了struct device指针，则调用of\_clk\_get\_by\_name接口，通过device tree接口获取clock指针。否则，如果没有提供设备指针，或者通过device tree不能正确获取clock，则进一步调用clk\_get\_sys。
>
> 这两个接口的定义如下。

2) of\_clk\_get\_by\_name

我们在“[Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”中已经提过，clock consumer会在本设备的DTS中，以clocks、clock-names为关键字，定义所需的clock。系统启动后，device tree会简单的解析，以struct device\_node指针的形式，保存在本设备的of\_node变量中。

而of\_clk\_get\_by\_name，就是通过扫描所有“clock-names”中的值，和传入的name比较，如果相同，获得它的index（即“clock-names”中的第几个），调用of\_clk\_get，取得clock指针。

```
   1: struct clk *of_clk_get_by_name(struct device_node *np, const char *name)
```

```
   2: {
```

```
   3:         struct clk *clk = ERR_PTR(-ENOENT);
```

```
   4:  
```

```
   5:         /* Walk up the tree of devices looking for a clock that matches */
```

```
   6:         while (np) {
```

```
   7:                 int index = 0;
```

```
   8:  
```

```
   9:                 /*
```

```
  10:                  * For named clocks, first look up the name in the
```

```
  11:                  * "clock-names" property.  If it cannot be found, then
```

```
  12:                  * index will be an error code, and of_clk_get() will fail.
```

```
  13:                  */
```

```
  14:                 if (name)
```

```
  15:                         index = of_property_match_string(np, "clock-names", name);
```

```
  16:                 clk = of_clk_get(np, index);
```

```
  17:                 if (!IS_ERR(clk))
```

```
  18:                         break;
```

```
  19:                 else if (name && index >= 0) {
```

```
  20:                         pr_err("ERROR: could not get clock %s:%s(%i)\n",
```

```
  21:                                 np->full_name, name ? name : "", index);
```

```
  22:                         return clk;
```

```
  23:                 }
```

```
  24:  
```

```
  25:                 /*
```

```
  26:                  * No matching clock found on this node.  If the parent node
```

```
  27:                  * has a "clock-ranges" property, then we can try one of its
```

```
  28:                  * clocks.
```

```
  29:                  */
```

```
  30:                 np = np->parent;
```

```
  31:                 if (np && !of_get_property(np, "clock-ranges", NULL))
```

```
  32:                         break;
```

```
  33:         }
```

```
  34:  
```

```
  35:         return clk;
```

```
  36: }
```

> 6~33行，是一个while循环，用于扫描所有的device\_node；
>
> 14~15行，只要name不为空，管它三七二十一，直接以name为参数，去和“clock-names”匹配，获得一个index；
>
> 16~18行，以返回的index为参数，调用of\_clk\_get。这个index可能是invalid，不过无所谓，最糟糕就是不能获得clock指针。如果成功获取，则退出，或者继续；
>
> 19~22行，一个警告，如果name和index均合法，但是不能获得指针，则视为异常状况；
>
> 25~32行，尝试”clock-ranges“熟悉，比较冷门，不介绍它。

再看一下of\_clk\_get接口。

```
   1: struct clk *of_clk_get(struct device_node *np, int index)
```

```
   2: {
```

```
   3:         struct of_phandle_args clkspec;
```

```
   4:         struct clk *clk;
```

```
   5:         int rc;
```

```
   6:  
```

```
   7:         if (index < 0)
```

```
   8:                 return ERR_PTR(-EINVAL);
```

```
   9:  
```

```
  10:         rc = of_parse_phandle_with_args(np, "clocks", "#clock-cells", index,
```

```
  11:                                         &clkspec);
```

```
  12:         if (rc)
```

```
  13:                 return ERR_PTR(rc);
```

```
  14:  
```

```
  15:         clk = of_clk_get_from_provider(&clkspec);
```

```
  16:         of_node_put(clkspec.np);
```

```
  17:         return clk;
```

```
  18: }
```

> 10~13行，通过of\_parse\_phandle\_with\_args接口，将index转换为struct of\_phandle\_args类型的参数句柄；
>
> 15行，调用of\_clk\_get\_from\_provider，获取clock指针。

of\_clk\_get\_from\_provider的实现位于drivers/clk/clk.c，通过便利of\_clk\_providers链表，并调用每一个provider的get回调函数，获取clock指针。如下：

```
   1: struct clk *of_clk_get_from_provider(struct of_phandle_args *clkspec)
```

```
   2: {
```

```
   3:         struct of_clk_provider *provider;
```

```
   4:         struct clk *clk = ERR_PTR(-ENOENT);
```

```
   5:  
```

```
   6:         /* Check if we have such a provider in our array */
```

```
   7:         mutex_lock(&of_clk_lock);
```

```
   8:         list_for_each_entry(provider, &of_clk_providers, link) {
```

```
   9:                 if (provider->node == clkspec->np)
```

```
  10:                         clk = provider->get(clkspec, provider->data);
```

```
  11:                 if (!IS_ERR(clk))
```

```
  12:                         break;
```

```
  13:         }
```

```
  14:         mutex_unlock(&of_clk_lock);
```

```
  15:  
```

```
  16:         return clk;
```

```
  17: }
```

注3：分析到这里之后，consumer侧的获取流程已经很清晰，再结合“[Linux common clock framework(2)\_clock provider](/pm_subsystem/clock_provider.html)”中所介绍的of\_clk\_add\_provider接口，整个流程都融汇贯通了。篇幅所限，有关of\_clk\_add\_provider接口的实现，本文就不再分析了，感兴趣的读者可以自行阅读kernel代码。

3）clk\_get\_sys

clk\_get\_sys接口是在调用者没有提供struct device指针或者通过of\_clk\_get\_xxx获取clock失败时，获取clock指针的另一种手段。基于kernel大力推行device tree的现状，蜗蜗不建议使用这种过时的手段，就不分析了。

##### 4.2 clk\_prepare/clk\_unprepare

prepare和unprepare的的代码位于drivers/clk/clk.c中，分别由内部接口\_\_clk\_prepare和\_\_clk\_unprepare实现具体动作，如下：

```
   1: int __clk_prepare(struct clk *clk)
```

```
   2: {
```

```
   3:         int ret = 0;
```

```
   4:  
```

```
   5:         if (!clk)
```

```
   6:                 return 0;
```

```
   7:  
```

```
   8:         if (clk->prepare_count == 0) {
```

```
   9:                 ret = __clk_prepare(clk->parent);
```

```
  10:                 if (ret)
```

```
  11:                         return ret;
```

```
  12:  
```

```
  13:                 if (clk->ops->prepare) {
```

```
  14:                         ret = clk->ops->prepare(clk->hw);
```

```
  15:                         if (ret) {
```

```
  16:                                 __clk_unprepare(clk->parent);
```

```
  17:                                 return ret;
```

```
  18:                         }
```

```
  19:                 }
```

```
  20:         }
```

```
  21:  
```

```
  22:         clk->prepare_count++;
```

```
  23:  
```

```
  24:         return 0;
```

```
  25: }
```

> prepare会维护一个prepare\_count，用于记录prepare的次数。且在prepare\_count为零时：
>
> 递归prepare自己的parent（有的话）；
>
> 调用clk ops中的prepare回调函数（有的话）。

unprepare类似，不再分析。

##### 4.3 clk\_enable/clk\_disable

enable/disable和prepare/unprepare的实现逻辑基本一致，需要注意的是，enable/disable时如果prepare\_count为0，则会报错并返回。

##### 4.4 clock rate有关的实现

clock rate有关的实现包括get、set和round三类，让我们依次说明。

1）clk\_get\_rate负责获取某个clock的当前rate，代码如下：

```
   1: /**
```

```
   2:  * clk_get_rate - return the rate of clk
```

```
   3:  * @clk: the clk whose rate is being returned
```

```
   4:  *
```

```
   5:  * Simply returns the cached rate of the clk, unless CLK_GET_RATE_NOCACHE flag
```

```
   6:  * is set, which means a recalc_rate will be issued.
```

```
   7:  * If clk is NULL then returns 0.
```

```
   8:  */
```

```
   9: unsigned long clk_get_rate(struct clk *clk)
```

```
  10: {
```

```
  11:         unsigned long rate;
```

```
  12:  
```

```
  13:         clk_prepare_lock();
```

```
  14:  
```

```
  15:         if (clk && (clk->flags & CLK_GET_RATE_NOCACHE))
```

```
  16:                 __clk_recalc_rates(clk, 0);
```

```
  17:  
```

```
  18:         rate = __clk_get_rate(clk);
```

```
  19:         clk_prepare_unlock();
```

```
  20:  
```

```
  21:         return rate;
```

```
  22: }
```

```
  23: EXPORT_SYMBOL_GPL(clk_get_rate);
```

> a）如果该clock设置了CLK\_GET\_RATE\_NOCACHE标志，获取rate前需要先调用\_\_clk\_recalc\_rates接口，根据当前硬件的实际情况，重新计算rate。
>   
> \_\_clk\_recalc\_rates的逻辑是：如果提供了recalc\_rate ops，以parent clock的rate为参数，调用该ops，否则，直接获取parent的clock值；然后，递归recalc所有child clock。
>
> b）调用\_\_clk\_get\_rate返回实际的rate值。

2）clk\_round\_rate，返回该clock支持的，和输入rate最接近的rate值（不做任何改动），实际是由内部函数\_\_clk\_round\_rate实现，代码如下：

```
   1: unsigned long __clk_round_rate(struct clk *clk, unsigned long rate)
```

```
   2: {
```

```
   3:         unsigned long parent_rate = 0;
```

```
   4:  
```

```
   5:         if (!clk)
```

```
   6:                 return 0;
```

```
   7:  
```

```
   8:         if (!clk->ops->round_rate) {
```

```
   9:                 if (clk->flags & CLK_SET_RATE_PARENT)
```

```
  10:                         return __clk_round_rate(clk->parent, rate);
```

```
  11:                 else
```

```
  12:                         return clk->rate;
```

```
  13:         }
```

```
  14:  
```

```
  15:         if (clk->parent)
```

```
  16:                 parent_rate = clk->parent->rate;
```

```
  17:  
```

```
  18:         return clk->ops->round_rate(clk->hw, rate, &parent_rate);
```

```
  19: }
```

> a）18行，如果该clock提供了round\_rate ops，直接调用该ops。
>
> 需要说明的是，round\_rate ops接受两个参数，一个是需要round的rate，另一个时parent rate（以指针的形式提供）。它的意义是，对有些clock来说，如果需要得到一个比较接近的值，需要同时round parent clock，因此会在该指针中返回round后的parent clock。
>
> b）9~10行，如果clock没有提供round\_rate ops，且设置了CLK\_SET\_RATE\_PARENT标志，则递归round parent clock，背后的思考是，直接使用parent clock所能提供的最接近的rate。
>
> c）11~12，最后一种情况，直接返回原值，意味着无法round。

3）clk\_set\_rate

set rate的逻辑比较复杂，代码如下：

```
   1: int clk_set_rate(struct clk *clk, unsigned long rate)
```

```
   2: {
```

```
   3:         struct clk *top, *fail_clk;
```

```
   4:         int ret = 0;
```

```
   5:  
```

```
   6:         /* prevent racing with updates to the clock topology */
```

```
   7:         clk_prepare_lock();
```

```
   8:  
```

```
   9:         /* bail early if nothing to do */
```

```
  10:         if (rate == clk->rate)
```

```
  11:                 goto out;
```

```
  12:  
```

```
  13:         if ((clk->flags & CLK_SET_RATE_GATE) && clk->prepare_count) {
```

```
  14:                 ret = -EBUSY;
```

```
  15:                 goto out;
```

```
  16:         }
```

```
  17:  
```

```
  18:         /* calculate new rates and get the topmost changed clock */
```

```
  19:         top = clk_calc_new_rates(clk, rate);
```

```
  20:         if (!top) {
```

```
  21:                 ret = -EINVAL;
```

```
  22:                 goto out;
```

```
  23:         }
```

```
  24:  
```

```
  25:         /* notify that we are about to change rates */
```

```
  26:         fail_clk = clk_propagate_rate_change(top, PRE_RATE_CHANGE);
```

```
  27:         if (fail_clk) {
```

```
  28:                 pr_warn("%s: failed to set %s rate\n", __func__,
```

```
  29:                                 fail_clk->name);
```

```
  30:                 clk_propagate_rate_change(top, ABORT_RATE_CHANGE);
```

```
  31:                 ret = -EBUSY;
```

```
  32:                 goto out;
```

```
  33:         }
```

```
  34:  
```

```
  35:         /* change the rates */
```

```
  36:         clk_change_rate(top);
```

```
  37:  
```

```
  38: out:
```

```
  39:         clk_prepare_unlock();
```

```
  40:  
```

```
  41:         return ret;
```

```
  42: }
```

> a）9~16，进行一些合法性判断。
>
> b）19~23行，调用clk\_calc\_new\_rates接口，将需要设置的rate缓存在new\_rate字段。
>
> 同时，获取设置该rate的话，需要修改到的最顶层的clock。背后的逻辑是：如果该clock的rate改变，有可能需要通过改动parent clock的rate来实现，依次递归。
>
> c）25~23，发送rate将要改变的通知。如果有clock不能接受改动，即set rate失败，再发送rate更改停止的通知。
>
> d）调用clk\_change\_rate，从最top的clock开始，依次设置新的rate。

注4：clock rate set有2种场景，一是只需修改自身的配置，即可达到rate set的目的。第二种是需要同时修改parent的rate（可向上递归）才能达成目的。看似简单的逻辑，里面却包含非常复杂的系统设计的知识。大家在使用clock framework，知道有这回事即可，并尽可能的不要使用第二种场景，以保持系统的简洁性。

##### 4.5 clock parent有关的实现

parent操作包括get parent和set parent两类。
  
get parent的逻辑非常简单，直接从clk->parent指针中获取即可。
  
set parent稍微复杂，需要执行reparent和recalc\_rates动作，具体不再描述了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/clock_framework_core.html)。
