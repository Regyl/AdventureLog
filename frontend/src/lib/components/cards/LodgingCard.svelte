<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from '../DeleteWarning.svelte';
	import { LODGING_TYPES_ICONS } from '$lib';
	import { formatDateInTimezone } from '$lib/dateUtils';
	import { formatAllDayDate } from '$lib/dateUtils';
	import { isAllDay } from '$lib';
	import CardCarousel from '../CardCarousel.svelte';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import CalendarRemove from '~icons/mdi/calendar-remove';
	import type { CollectionItineraryItem } from '$lib/types';

	const dispatch = createEventDispatcher();

	function getLodgingIcon(type: string) {
		if (type in LODGING_TYPES_ICONS) {
			return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS];
		} else {
			return '🏨';
		}
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

	export let lodging: Lodging;
	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let readOnly: boolean = false;
	export let itineraryItem: CollectionItineraryItem | null = null;

	let isWarningModalOpen: boolean = false;

	function editTransportation() {
		dispatch('edit', lodging);
	}

	async function deleteTransportation() {
		let res = await fetch(`/api/lodging/${lodging.id}`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			console.log($t('transportation.transportation_delete_error'));
		} else {
			addToast('info', $t('transportation.transportation_deleted'));
			isWarningModalOpen = false;
			dispatch('delete', lodging.id);
		}
	}

	async function removeFromItinerary() {
		let itineraryItemId = itineraryItem?.id;
		let res = await fetch(`/api/itineraries/${itineraryItemId}`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('info', $t('itinerary.item_remove_success'));
			dispatch('removeFromItinerary', itineraryItem);
		} else {
			addToast('error', $t('itinerary.item_remove_error'));
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_lodging')}
		button_text="Delete"
		description={$t('adventures.lodging_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteTransportation}
	/>
{/if}

<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="lodging-card"
>
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel images={lodging.images} icon={getLodgingIcon(lodging.type)} name={lodging.name} />

		<!-- Privacy Indicator -->
		<div class="absolute top-2 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={lodging.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="badge badge-sm p-1 rounded-full text-base-content shadow-sm"
					role="img"
					aria-label={lodging.is_public ? $t('adventures.public') : $t('adventures.private')}
				>
					{#if lodging.is_public}
						<Eye class="w-4 h-4" />
					{:else}
						<EyeOff class="w-4 h-4" />
					{/if}
				</div>
			</div>
		</div>

		<!-- Category Badge -->
		{#if lodging.type}
			<div class="absolute bottom-4 left-4">
				<div class="badge badge-primary shadow-lg font-medium">
					{$t(`lodging.${lodging.type}`)}
					{getLodgingIcon(lodging.type)}
				</div>
			</div>
		{/if}
	</div>
	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<h2 class="text-lg font-semibold line-clamp-2">{lodging.name}</h2>

			{#if !readOnly && (lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid)))}
				<details class="dropdown dropdown-end relative z-50">
					<summary class="btn btn-square btn-sm p-1 text-base-content">
						<DotsHorizontal class="w-5 h-5" />
					</summary>
					<ul
						class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300"
					>
						<li>
							<button on:click={editTransportation} class="flex items-center gap-2">
								<FileDocumentEdit class="w-4 h-4" />
								{$t('transportation.edit')}
							</button>
						</li>
						{#if itineraryItem && itineraryItem.id}
							<div class="divider my-1"></div>
							<li>
								<button
									on:click={() => removeFromItinerary()}
									class="text-error flex items-center gap-2"
								>
									<CalendarRemove class="w-4 h-4 text-error" />
									{$t('itinerary.remove_from_itinerary')}
								</button>
							</li>
						{/if}
						<div class="divider my-1"></div>
						<li>
							<button
								class="text-error flex items-center gap-2"
								on:click={() => (isWarningModalOpen = true)}
							>
								<TrashCanOutline class="w-4 h-4" />
								{$t('adventures.delete')}
							</button>
						</li>
					</ul>
				</details>
			{/if}
		</div>

		<!-- Location Info (Compact) -->
		{#if lodging.location}
			<div class="flex items-center gap-2 text-sm text-base-content/70">
				<MapMarker class="w-4 h-4 text-primary" />
				<span class="truncate max-w-[18rem]">{lodging.location}</span>
			</div>
		{/if}

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if lodging.check_in}
				<div class="flex items-center gap-1">
					<span class="font-medium">
						{#if isAllDay(lodging.check_in)}
							{formatAllDayDate(lodging.check_in)}
						{:else}
							{formatDateInTimezone(lodging.check_in, lodging.timezone)}
						{/if}
					</span>
				</div>
			{/if}

			{#if lodging.check_out && lodging.check_in}
				<span class="text-base-content/40">→</span>
				<div class="flex items-center gap-1">
					<span class="font-medium">
						{#if isAllDay(lodging.check_out)}
							{formatAllDayDate(lodging.check_out)}
						{:else}
							{formatDateInTimezone(lodging.check_out, lodging.timezone)}
						{/if}
					</span>
				</div>
			{/if}

			{#if lodging.rating}
				<div class="flex items-center gap-1">
					<div class="flex -ml-1">
						{#each renderStars(lodging.rating) as filled}
							{#if filled}
								<Star class="w-4 h-4 text-warning fill-current" />
							{:else}
								<StarOutline class="w-4 h-4 text-base-content/30" />
							{/if}
						{/each}
					</div>
					<span class="text-xs text-base-content/60">({lodging.rating}/5)</span>
				</div>
			{/if}
		</div>

		<!-- Additional Info (for owner only) -->
		{#if lodging.user == user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
			<div class="flex flex-wrap gap-2">
				{#if lodging.reservation_number}
					<div class="badge badge-ghost badge-sm">
						{$t('adventures.reservation')}: {lodging.reservation_number}
					</div>
				{/if}
				{#if lodging.price}
					<div class="badge badge-ghost badge-sm">
						{lodging.price}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
