---
title: "linux kernel内存碎片防治技术"
date: 2015-11-02T10:24:54+08:00
url: "/memory_management/memory-fragment.html"
gid: "228"
emlog_type: "blog"
summary: "Linux kernel 组织管理物理内存的方式是 buddy system （伙伴系统），而物理内存碎片正式 buddy system 的弱点之一，为了预防以及解决碎片问题， kernel 采取了一些实用技术，这里将对这些技术进行总结归纳。"
author: "itrocker"
category: "内存管理"
category_alias: "memory_management"
tags: ["内存碎片"]
views: 36829
comment_count: 20
aliases:
  - "/memory_management/228.html"
  - "/228.html"
---

Linux kernel组织管理物理内存的方式是buddy
system（伙伴系统），而物理内存碎片正式buddy system的弱点之一，为了预防以及解决碎片问题，kernel采取了一些实用技术，这里将对这些技术进行总结归纳。

**1** **低内存时整合碎片**

从buddy申请内存页，如果找不到合适的页，则会进行两步调整内存的工作，compact和reclaim。前者是为了整合碎片，以得到更大的连续内存；后者是回收不一定必须占用内存的缓冲内存。这里重点了解comact，整个流程大致如下：

\_\_alloc\_pages\_nodemask

-> \_\_alloc\_pages\_slowpath

-> \_\_alloc\_pages\_direct\_compact

-> try\_to\_compact\_pages

-> compact\_zone\_order

-> compact\_zone

-> isolate\_migratepages

-> migrate\_pages

-> release\_freepages

并不是所有申请不到内存的场景都会compact，首先要满足order大于0，并且gfp\_mask携带\_\_GFP\_FS和\_\_GFP\_IO；另外，需要zone的剩余内存情况满足一定条件，kernel称之为“碎片指数”（fragmentation index），这个值在0~1000之间，默认碎片指数大于500时才能进行compact，可以通过proc文件extfrag\_threshold来调整这个默认值。fragmentation index通过fragmentation\_index函数来计算：

```
        /*
	 * Index is between 0 and 1000
	 *
	 * 0 => allocation would fail due to lack of memory
	 * 1000 => allocation would fail due to fragmentation
	 */
	return 1000 - div_u64( (1000+(div_u64(info->free_pages * 1000ULL, requested))), info->free_blocks_total)
```

在整合内存碎片的过程中，碎片页只会在本zone的内部移动，将位于zone低地址的页尽量移到zone的末端。申请新的页面位置通过compaction\_alloc函数实现。

移动过程又分为同步和异步，内存申请失败后第一次compact将会使用异步，后续reclaim之后将会使用同步。同步过程只移动当面未被使用的页，异步过程将遍历并等待所有MOVABLE的页使用完成后进行移动。

**2** **按可移动性组织页**

按照可移动性将内存页分为以下三个类型：

UNMOVABLE：在内存中位置固定，不能随意移动。kernel分配的内存基本属于这个类型；

RECLAIMABLE：不能移动，但可以删除回收。例如文件映射内存；

MOVABLE：可以随意移动，用户空间的内存基本属于这个类型。

申请内存时，根据可移动性，首先在指定类型的空闲页中申请内存，每个zone的空闲内存组织方式如下：

```
struct zone {
......
struct free_area    free_area[MAX_ORDER];
......
}

struct free_area {
	struct list_head	free_list[MIGRATE_TYPES];
	unsigned long		nr_free;
};
```

当在指定类型的free\_area申请不到内存时，可以从备用类型挪用，挪用之后的内存就会释放到新指定的类型列表中，kernel把这个过程称为“盗用”。

备用类型优先级列表如下定义：

```
static int fallbacks[MIGRATE_TYPES][4] = {
	[MIGRATE_UNMOVABLE]   = { MIGRATE_RECLAIMABLE, MIGRATE_MOVABLE,     MIGRATE_RESERVE },
	[MIGRATE_RECLAIMABLE] = { MIGRATE_UNMOVABLE,   MIGRATE_MOVABLE,     MIGRATE_RESERVE },
#ifdef CONFIG_CMA
	[MIGRATE_MOVABLE]     = { MIGRATE_CMA,         MIGRATE_RECLAIMABLE, MIGRATE_UNMOVABLE, MIGRATE_RESERVE },
	[MIGRATE_CMA]         = { MIGRATE_RESERVE }, /* Never used */
#else
	[MIGRATE_MOVABLE]     = { MIGRATE_RECLAIMABLE, MIGRATE_UNMOVABLE,   MIGRATE_RESERVE },
#endif
	[MIGRATE_RESERVE]     = { MIGRATE_RESERVE }, /* Never used */
#ifdef CONFIG_MEMORY_ISOLATION
	[MIGRATE_ISOLATE]     = { MIGRATE_RESERVE }, /* Never used */
#endif
};
```

  

值得注意的是并不是所有场景都适合按可移动性组织页，当内存大小不足以分配到各种类型时，就不适合启用可移动性。有个全局变量来表示是否启用，在内存初始化时设置：

```
void __ref build_all_zonelists(pg_data_t *pgdat, struct zone *zone)
{
......
    if (vm_total_pages < (pageblock_nr_pages * MIGRATE_TYPES))
		page_group_by_mobility_disabled = 1;
	else
		page_group_by_mobility_disabled = 0;
......
}
```

如果page\_group\_by\_mobility\_disabled，则所有内存都是不可移动的。

其中有个参数决定了每个内存区域至少拥有的页，pageblock\_nr\_pages，它的定义如下：

#define pageblock\_order HUGETLB\_PAGE\_ORDER

```
#else /* CONFIG_HUGETLB_PAGE */
/* If huge pages are not used, group by MAX_ORDER_NR_PAGES */
#define pageblock_order		(MAX_ORDER-1)
#endif /* CONFIG_HUGETLB_PAGE */
#define pageblock_nr_pages	(1UL << pageblock_order)
```

在系统初始化期间，所有页都被标记为MOVABLE：

```
void __meminit memmap_init_zone(unsigned long size, int nid, unsigned long zone,
		unsigned long start_pfn, enum memmap_context context)
{
......
		if ((z->zone_start_pfn <= pfn)
		    && (pfn < zone_end_pfn(z))
		    && !(pfn & (pageblock_nr_pages - 1)))
			set_pageblock_migratetype(page, MIGRATE_MOVABLE);
......
}
```

其它可移动性类型的页都是后来产生的，也就是前面说的“盗取”。在这种情况发生时，通常会“盗取”fallback中更高优先级、更大块连续的页，从而避免小碎片的产生。

```
/* Remove an element from the buddy allocator from the fallback list */
static inline struct page *
__rmqueue_fallback(struct zone *zone, int order, int start_migratetype)
{
......
	/* Find the largest possible block of pages in the other list */
	for (current_order = MAX_ORDER-1; current_order >= order;
						--current_order) {
		for (i = 0;; i++) {
			migratetype = fallbacks[start_migratetype][i];
......
}
```

可以通过/proc/pageteypeinfo查看当前系统各种类型的页分布。

**3** **虚拟可移动内存域**

在依据可移动性组织页的技术之前，还有一个方法已经合入kernel，那就是虚拟内存域：ZONE\_MOVABLE。基本思想很简单：把内存分为两部分，可移动的和不可移动的。

```
enum zone_type {
#ifdef CONFIG_ZONE_DMA
	ZONE_DMA,
#endif
#ifdef CONFIG_ZONE_DMA32
	ZONE_DMA32,
#endif
	ZONE_NORMAL,
#ifdef CONFIG_HIGHMEM
	ZONE_HIGHMEM,
#endif
	ZONE_MOVABLE,
	__MAX_NR_ZONES
};
```

ZONE\_MOVABLE的启用需要指定kernel参数kernelcore或者movablecore，kernelcore用来指定不可移动的内存数量，movablecore指定可移动的内存大小，如果两个都指定，取不可移动内存数量较大的一个。如果都不指定，则不启动。

与其它内存域不同的是ZONE\_MOVABLE不关联任何物理内存范围，该域的内存取自高端内存域或者普通内存域。

find\_zone\_movable\_pfns\_for\_nodes用来计算每个node中ZONE\_MOVABLE的内存数量，采用的内存区域通常是每个node的最高内存域，在函数find\_usable\_zone\_for\_movable中体现。

在对每个node分配ZONE\_MOVABLE内存时，kernelcore会被平均分配到各个Node：

kernelcore\_node = required\_kernelcore /
usable\_nodes;

在kernel alloc page时，如果gfp\_flag同时指定了\_\_GFP\_HIGHMEM和\_\_GFP\_MOVABLE，则会从ZONE\_MOVABLE内存域申请内存。
