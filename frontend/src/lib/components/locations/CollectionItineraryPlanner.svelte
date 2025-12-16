<script lang="ts">
	// @ts-nocheck
	import type {
		Collection,
		CollectionItineraryItem,
		Location,
		Transportation,
		Lodging,
		Note,
		Checklist
	} from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import { dndzone, TRIGGERS, SHADOW_ITEM_MARKER_PROPERTY_NAME } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';
	import CalendarBlank from '~icons/mdi/calendar-blank';
	import LocationCard from '$lib/components/LocationCard.svelte';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import LodgingCard from '$lib/components/LodgingCard.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import ChecklistCard from '$lib/components/ChecklistCard.svelte';

	export let collection: Collection;
	export let user: any;

	const flipDurationMs = 200;

	// Extended itinerary item with resolved object
	type ResolvedItineraryItem = CollectionItineraryItem & {
		resolvedObject: Location | Transportation | Lodging | Note | Checklist | null;
	};

	// Group itinerary items by day
	type DayGroup = {
		date: string;
		displayDate: string;
		items: ResolvedItineraryItem[];
	};

	$: days = groupItemsByDay(collection);
	$: unscheduledItems = getUnscheduledItems(collection);

	function resolveItineraryItem(
		item: CollectionItineraryItem,
		collection: Collection
	): ResolvedItineraryItem {
		let resolvedObject = null;

		// Resolve based on item.type which tells us the object type
		const objectType = item.item?.type || '';

		if (objectType === 'location') {
			// Find location by ID
			resolvedObject = collection.locations?.find((loc) => loc.id === item.object_id) || null;
		} else if (objectType === 'transportation') {
			resolvedObject = collection.transportations?.find((t) => t.id === item.object_id) || null;
		} else if (objectType === 'lodging') {
			resolvedObject = collection.lodging?.find((l) => l.id === item.object_id) || null;
		} else if (objectType === 'note') {
			resolvedObject = collection.notes?.find((n) => n.id === item.object_id) || null;
		} else if (objectType === 'checklist') {
			resolvedObject = collection.checklists?.find((c) => c.id === item.object_id) || null;
		}

		return {
			...item,
			resolvedObject
		};
	}

	function groupItemsByDay(collection: Collection): DayGroup[] {
		// Build a map of date -> resolved items from existing itinerary entries
		const grouped = new Map<string, ResolvedItineraryItem[]>();

		collection.itinerary?.forEach((item) => {
			if (item.date) {
				if (!grouped.has(item.date)) grouped.set(item.date, []);
				const resolved = resolveItineraryItem(item, collection);
				grouped.get(item.date)!.push(resolved);
			}
		});

		// Determine a date range to display. Prefer explicit collection start/end if present,
		// otherwise use min/max dates found in itinerary items. If no dates at all, return []
		let startDateISO: string | null = null;
		let endDateISO: string | null = null;

		if (collection.start_date && collection.end_date) {
			startDateISO = collection.start_date;
			endDateISO = collection.end_date;
		} else {
			// derive from itinerary dates if available
			const dates = Array.from(grouped.keys()).sort();
			if (dates.length > 0) {
				startDateISO = dates[0];
				endDateISO = dates[dates.length - 1];
			}
		}

		if (!startDateISO || !endDateISO) return [];

		const start = DateTime.fromISO(startDateISO).startOf('day');
		const end = DateTime.fromISO(endDateISO).startOf('day');

		const days: DayGroup[] = [];
		for (let dt = start; dt <= end; dt = dt.plus({ days: 1 })) {
			const iso = dt.toISODate();
			const items = (grouped.get(iso) || []).sort((a, b) => a.order - b.order);
			days.push({
				date: iso,
				displayDate: dt.toFormat('cccc, LLLL d, yyyy'),
				items
			});
		}

		return days;
	}

	function getUnscheduledItems(collection: Collection): any[] {
		// Get all items that are linked to collection but not in itinerary
		const scheduledIds = new Set(collection.itinerary?.map((item) => item.object_id) || []);

		const unscheduled: any[] = [];

		// Check locations
		collection.locations?.forEach((location) => {
			if (!scheduledIds.has(location.id)) {
				unscheduled.push({ type: 'location', item: location });
			}
		});

		// Check transportation
		collection.transportations?.forEach((transport) => {
			if (!scheduledIds.has(transport.id)) {
				unscheduled.push({ type: 'transportation', item: transport });
			}
		});

		// Check lodging
		collection.lodging?.forEach((lodge) => {
			if (!scheduledIds.has(lodge.id)) {
				unscheduled.push({ type: 'lodging', item: lodge });
			}
		});

		// Check notes
		collection.notes?.forEach((note) => {
			if (!scheduledIds.has(note.id)) {
				unscheduled.push({ type: 'note', item: note });
			}
		});

		// Check checklists
		collection.checklists?.forEach((checklist) => {
			if (!scheduledIds.has(checklist.id)) {
				unscheduled.push({ type: 'checklist', item: checklist });
			}
		});

		return unscheduled;
	}

	function isMultiDay(item: ResolvedItineraryItem): boolean {
		if (item.start_datetime && item.end_datetime) {
			const start = DateTime.fromISO(item.start_datetime);
			const end = DateTime.fromISO(item.end_datetime);
			return !start.hasSame(end, 'day');
		}
		return false;
	}

	function handleDndConsider(dayIndex: number, e: CustomEvent) {
		const { items: newItems } = e.detail;
		// Update the local state immediately for smooth drag feedback
		days[dayIndex].items = newItems;
		days = [...days];
	}

	function handleDndFinalize(dayIndex: number, e: CustomEvent) {
		const { items: newItems } = e.detail;

		// Update local state
		days[dayIndex].items = newItems;
		days = [...days];

		// TODO: Add backend save functionality here when ready
		// Example:
		// if (info.trigger === TRIGGERS.DROPPED_INTO_ZONE || info.trigger === TRIGGERS.DROPPED_INTO_ANOTHER) {
		//   await saveReorderedItems(days[dayIndex].date, newItems);
		// }
	}
</script>

{#if days.length === 0 && unscheduledItems.length === 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body text-center py-12">
			<CalendarBlank class="w-16 h-16 mx-auto mb-4 opacity-50" />
			<h3 class="text-2xl font-bold mb-2">No Itinerary Yet</h3>
			<p class="opacity-70">Start planning your trip by adding items to specific days.</p>
		</div>
	</div>
{:else}
	<div class="space-y-6">
		<!-- Scheduled Days -->
		{#each days as day, dayIndex}
			<div class="card bg-base-200 shadow-xl">
				<div class="card-body">
					<!-- Day Header -->
					<div class="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
						<CalendarBlank class="w-6 h-6 text-primary" />
						<h3 class="text-xl font-bold">{day.displayDate}</h3>
						<div class="badge badge-primary badge-outline ml-auto">
							{day.items.length}
							{day.items.length === 1 ? 'item' : 'items'}
						</div>
					</div>

					<!-- Day Items -->
					<div class="space-y-4">
						{#if day.items.length === 0}
							<div
								class="card bg-base-100 shadow-sm border border-dashed border-base-300 p-4 text-center"
							>
								<div class="card-body p-2">
									<CalendarBlank class="w-8 h-8 mx-auto mb-2 opacity-40" />
									<p class="opacity-70">No plans for this day</p>
								</div>
							</div>
						{:else}
							<div
								use:dndzone={{
									items: day.items,
									flipDurationMs,
									dropTargetStyle: { outline: 'none', border: 'none' },
									dragDisabled: false
								}}
								on:consider={(e) => handleDndConsider(dayIndex, e)}
								on:finalize={(e) => handleDndFinalize(dayIndex, e)}
								class="space-y-4"
							>
								{#each day.items as item, index (item.id)}
									{@const objectType = item.item?.type || ''}
									{@const resolvedObj = item.resolvedObject}
									{@const multiDay = isMultiDay(item)}
									{@const isDraggingShadow = item[SHADOW_ITEM_MARKER_PROPERTY_NAME]}

									<div
										class="group relative transition-all duration-200 {isDraggingShadow
											? 'opacity-40 scale-95'
											: 'hover:shadow-lg'}"
										animate:flip={{ duration: flipDurationMs }}
									>
										{#if resolvedObj}
											<!-- Drag Handle Container -->
											<div
												class="absolute -left-3 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
												title="Drag to reorder"
											>
												<div
													class="bg-base-300 hover:bg-primary hover:text-primary-content rounded-lg p-2 cursor-grab active:cursor-grabbing shadow-md transition-all duration-200 hover:scale-110"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														class="h-5 w-5"
														fill="none"
														viewBox="0 0 24 24"
														stroke="currentColor"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2.5"
															d="M8 9h8M8 15h8"
														/>
													</svg>
												</div>
											</div>

											<!-- Order Badge -->
											<div class="absolute -left-3 -top-3 z-10">
												<div
													class="flex items-center justify-center w-7 h-7 rounded-full bg-primary text-primary-content font-bold text-xs shadow-lg"
												>
													{index + 1}
												</div>
											</div>

											<!-- Multi-day indicator for lodging -->
											{#if multiDay && objectType === 'lodging'}
												<div class="absolute -right-3 -top-3 z-10">
													<div
														class="badge badge-info badge-sm shadow-lg gap-1 px-3 py-3 font-semibold"
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
															/>
														</svg>
														Overnight
													</div>
												</div>
											{/if}

											<!-- Card with smooth transition -->
											<div class="transition-all duration-200">
												<!-- Display the appropriate card based on type -->
												{#if objectType === 'location'}
													<LocationCard adventure={resolvedObj} {user} collection={null} />
												{:else if objectType === 'transportation'}
													<TransportationCard transportation={resolvedObj} {user} {collection} />
												{:else if objectType === 'lodging'}
													<LodgingCard lodging={resolvedObj} {user} {collection} />
												{:else if objectType === 'note'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<NoteCard note={resolvedObj} {user} {collection} />
												{:else if objectType === 'checklist'}
													<!-- @ts-ignore - TypeScript can't narrow union type properly -->
													<ChecklistCard checklist={resolvedObj} {user} {collection} />
												{/if}
											</div>
										{:else}
											<!-- Fallback for unresolved items -->
											<div class="alert alert-warning">
												<span>⚠️ Item not found (ID: {item.object_id})</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/each}

		<!-- Unscheduled Items -->
		{#if unscheduledItems.length > 0}
			<div class="card bg-base-200 shadow-xl border-2 border-dashed border-base-300">
				<div class="card-body">
					<!-- Unscheduled Header -->
					<div class="flex items-center gap-3 mb-4 pb-4 border-b border-base-300">
						<div class="w-6 h-6 rounded-full border-2 border-dashed border-base-content/30"></div>
						<h3 class="text-xl font-bold opacity-70">Unscheduled Items</h3>
						<div class="badge badge-ghost ml-auto">
							{unscheduledItems.length}
							{unscheduledItems.length === 1 ? 'item' : 'items'}
						</div>
					</div>

					<p class="text-sm opacity-70 mb-4">
						These items are linked to this trip but haven't been added to a specific day yet.
					</p>

					<!-- Unscheduled Items List -->
					<div class="space-y-4">
						{#each unscheduledItems as { type, item }}
							<div class="relative opacity-60 hover:opacity-100 transition-opacity">
								<!-- "Add to itinerary" indicator -->
								<div class="absolute -right-2 top-2 z-10">
									<button class="btn btn-circle btn-sm btn-primary" title="Add to itinerary">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="h-4 w-4"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 4v16m8-8H4"
											/>
										</svg>
									</button>
								</div>

								<!-- Display the appropriate card -->
								{#if type === 'location'}
									<LocationCard adventure={item} {user} collection={null} />
								{:else if type === 'transportation'}
									<TransportationCard transportation={item} {user} {collection} />
								{:else if type === 'lodging'}
									<LodgingCard lodging={item} {user} {collection} />
								{:else if type === 'note'}
									<NoteCard note={item} {user} {collection} />
								{:else if type === 'checklist'}
									<ChecklistCard checklist={item} {user} {collection} />
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
