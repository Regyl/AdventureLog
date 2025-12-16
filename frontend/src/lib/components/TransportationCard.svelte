<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import DeleteWarning from './DeleteWarning.svelte';
	// import ArrowDownThick from '~icons/mdi/arrow-down-thick';
	import { TRANSPORTATION_TYPES_ICONS } from '$lib';
	import { formatAllDayDate, formatDateInTimezone } from '$lib/dateUtils';
	import { isAllDay } from '$lib';
	import CardCarousel from './CardCarousel.svelte';

	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';

	function getTransportationIcon(type: string) {
		if (type in TRANSPORTATION_TYPES_ICONS) {
			return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS];
		} else {
			return '🚗';
		}
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

	const dispatch = createEventDispatcher();

	export let transportation: Transportation;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	const toMiles = (km: any) => (Number(km) * 0.621371).toFixed(1);

	let isWarningModalOpen: boolean = false;

	function editTransportation() {
		dispatch('edit', transportation);
	}

	async function deleteTransportation() {
		let res = await fetch(`/api/transportations/${transportation.id}`, {
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
			dispatch('delete', transportation.id);
		}
	}
</script>

{#if isWarningModalOpen}
	<DeleteWarning
		title={$t('adventures.delete_transportation')}
		button_text="Delete"
		description={$t('adventures.transportation_delete_confirm')}
		is_warning={false}
		on:close={() => (isWarningModalOpen = false)}
		on:confirm={deleteTransportation}
	/>
{/if}

<div
	class="card w-full max-w-md bg-base-300 shadow hover:shadow-md transition-all duration-200 border border-base-300 group"
	aria-label="transportation-card"
>
	<!-- Image Section with Overlay -->
	<div class="relative overflow-hidden rounded-t-2xl">
		<CardCarousel
			images={transportation.images}
			icon={getTransportationIcon(transportation.type)}
			name={transportation.name}
		/>

		<!-- Privacy Indicator -->
		<div class="absolute top-2 right-4">
			<div
				class="tooltip tooltip-left"
				data-tip={transportation.is_public ? $t('adventures.public') : $t('adventures.private')}
			>
				<div
					class="badge badge-sm p-1 rounded-full text-base-content shadow-sm"
					role="img"
					aria-label={transportation.is_public ? $t('adventures.public') : $t('adventures.private')}
				>
					{#if transportation.is_public}
						<Eye class="w-4 h-4" />
					{:else}
						<EyeOff class="w-4 h-4" />
					{/if}
				</div>
			</div>
		</div>

		<!-- Category Badge -->
		{#if transportation.type}
			<div class="absolute bottom-4 left-4">
				<div class="badge badge-primary shadow-lg font-medium">
					{$t(`transportation.modes.${transportation.type}`)}
					{getTransportationIcon(transportation.type)}
				</div>
			</div>
		{/if}
	</div>

	<div class="card-body p-4 space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<h2 class="text-lg font-semibold line-clamp-2">{transportation.name}</h2>

			{#if transportation.user === user?.uuid || (collection && user && collection.shared_with?.includes(user.uuid))}
				<div class="dropdown dropdown-end">
					<div tabindex="0" role="button" class="btn btn-square btn-sm p-1 text-base-content">
						<DotsHorizontal class="w-5 h-5" />
					</div>
					<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
					<ul
						tabindex="0"
						class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow-lg border border-base-300"
					>
						<li>
							<button on:click={editTransportation} class="flex items-center gap-2">
								<FileDocumentEdit class="w-4 h-4" />
								{$t('transportation.edit')}
							</button>
						</li>
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
				</div>
			{/if}
		</div>

		<!-- Route Info (Compact) -->
		<div class="space-y-2">
			{#if transportation.from_location && transportation.to_location}
				<div class="flex items-center gap-2 text-sm text-base-content/70">
					<span class="font-medium">{$t('adventures.route')}:</span>
					<span class="truncate">{transportation.from_location} → {transportation.to_location}</span
					>
				</div>
			{:else if transportation.from_location}
				<div class="flex items-center gap-2 text-sm text-base-content/70">
					<span class="font-medium">{$t('adventures.from')}:</span>
					<span class="truncate">{transportation.from_location}</span>
				</div>
			{:else if transportation.to_location}
				<div class="flex items-center gap-2 text-sm text-base-content/70">
					<span class="font-medium">{$t('adventures.to')}:</span>
					<span class="truncate">{transportation.to_location}</span>
				</div>
			{/if}

			{#if transportation.type === 'plane' && transportation.flight_number}
				<div class="flex items-center gap-2 text-sm text-base-content/70">
					<span class="font-medium">{$t('adventures.flight')}:</span>
					<span>{transportation.flight_number}</span>
				</div>
			{/if}
		</div>

		<!-- Inline Stats -->
		<div class="flex flex-wrap items-center gap-3 text-sm text-base-content/70">
			{#if transportation.date}
				<div class="flex items-center gap-1">
					<span class="font-medium">
						{#if isAllDay(transportation.date) && (!transportation.end_date || isAllDay(transportation.end_date))}
							{formatAllDayDate(transportation.date)}
						{:else}
							{formatDateInTimezone(transportation.date, transportation.start_timezone)}
						{/if}
					</span>
				</div>
			{/if}

			{#if transportation.distance && !isNaN(+transportation.distance)}
				<div class="badge badge-ghost badge-sm">
					{user?.measurement_system === 'imperial'
						? `${toMiles(transportation.distance)} mi`
						: `${(+transportation.distance).toFixed(1)} km`}
				</div>
			{/if}

			{#if transportation.rating}
				<div class="flex items-center gap-1">
					<div class="flex -ml-1">
						{#each renderStars(transportation.rating) as filled}
							{#if filled}
								<Star class="w-4 h-4 text-warning fill-current" />
							{:else}
								<StarOutline class="w-4 h-4 text-base-content/30" />
							{/if}
						{/each}
					</div>
					<span class="text-xs text-base-content/60">({transportation.rating}/5)</span>
				</div>
			{/if}
		</div>
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
