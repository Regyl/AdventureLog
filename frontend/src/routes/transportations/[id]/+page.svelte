<script lang="ts">
	import type { Transportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import ClipboardList from '~icons/mdi/clipboard-list';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import { getBasemapUrl, isAllDay, TRANSPORTATION_TYPES_ICONS } from '$lib';
	import Star from '~icons/mdi/star';
	import StarOutline from '~icons/mdi/star-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import CalendarRange from '~icons/mdi/calendar-range';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import OpenInNew from '~icons/mdi/open-in-new';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import CardAccountDetails from '~icons/mdi/card-account-details';
	import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';
	import TransportationModal from '$lib/components/transportation/TransportationModal.svelte';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	export let data: PageData;
	console.log(data);

	let transportation: Transportation;
	let currentSlide = 0;

	function goToSlide(index: number) {
		currentSlide = index;
	}

	let notFound: boolean = false;
	let mapCenter: [number, number] | null = null;
	let modalInitialIndex: number = 0;
	let isImageModalOpen: boolean = false;
	let isEditModalOpen: boolean = false;

	function getTransportationIcon(type: string) {
		if (type in TRANSPORTATION_TYPES_ICONS) {
			return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS];
		}
		return '🚗';
	}

	function renderStars(rating: number) {
		const stars = [];
		for (let i = 1; i <= 5; i++) {
			stars.push(i <= rating);
		}
		return stars;
	}

	onMount(async () => {
		if (data.props.transportation) {
			transportation = data.props.transportation;
			transportation.images.sort((a, b) => {
				if (a.is_primary && !b.is_primary) {
					return -1;
				} else if (!a.is_primary && b.is_primary) {
					return 1;
				} else {
					return 0;
				}
			});
		} else {
			notFound = true;
		}
	});

	$: mapCenter = transportation ? getMapCenter(transportation) : null;

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	function getRouteLabel() {
		if (!transportation) return '';
		if (transportation.from_location && transportation.to_location) {
			return `${transportation.from_location} → ${transportation.to_location}`;
		}
		return transportation.from_location ?? transportation.to_location ?? '';
	}

	function formatTravelWindow(
		start: string | null,
		end: string | null,
		startTimezone: string | null,
		endTimezone: string | null
	) {
		if (!start && !end) return null;

		const formatDate = (date: string | null, timezone: string | null) => {
			if (!date) return '';
			if (isAllDay(date)) {
				return formatAllDayDate(date);
			}
			return formatDateInTimezone(date, timezone);
		};

		if (start && end) {
			return `${formatDate(start, startTimezone)} → ${formatDate(end, endTimezone ?? startTimezone)}`;
		} else if (start) {
			return `${$t('adventures.start') ?? 'Start'}: ${formatDate(start, startTimezone)}`;
		} else if (end) {
			return `${$t('adventures.end') ?? 'End'}: ${formatDate(end, endTimezone)}`;
		}
		return null;
	}

	function calculateDuration(
		start: string | null,
		end: string | null,
		startTimezone: string | null,
		endTimezone: string | null
	): string | null {
		if (!start || !end) return null;

		const startDT = DateTime.fromISO(start, { zone: startTimezone ?? 'UTC' });
		const endDT = DateTime.fromISO(end, { zone: endTimezone ?? startTimezone ?? 'UTC' });

		if (!startDT.isValid || !endDT.isValid) return null;

		const totalMinutes = Math.round(endDT.diff(startDT, 'minutes').minutes ?? 0);
		if (totalMinutes <= 0) return null;

		const days = Math.floor(totalMinutes / (60 * 24));
		const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
		const minutes = totalMinutes % 60;

		const parts: string[] = [];
		if (days) parts.push(`${days}d`);
		if (hours) parts.push(`${hours}h`);
		if (minutes) parts.push(`${minutes}m`);

		return parts.join(' ');
	}

	function hasOriginCoordinates(item: Transportation) {
		return item.origin_latitude !== null && item.origin_longitude !== null;
	}

	function hasDestinationCoordinates(item: Transportation) {
		return item.destination_latitude !== null && item.destination_longitude !== null;
	}

	function getMapCenter(item: Transportation): [number, number] | null {
		if (hasOriginCoordinates(item)) {
			return [item.origin_longitude as number, item.origin_latitude as number];
		}
		if (hasDestinationCoordinates(item)) {
			return [item.destination_longitude as number, item.destination_latitude as number];
		}
		return null;
	}
</script>

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">Transportation not found</h1>
				<p class="text-lg opacity-70 mb-8">{$t('adventures.location_not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isEditModalOpen}
	<TransportationModal
		on:close={() => (isEditModalOpen = false)}
		user={data.user}
		transportationToEdit={transportation}
		bind:transportation
	/>
{/if}

{#if isImageModalOpen}
	<ImageDisplayModal
		images={transportation.images}
		initialIndex={modalInitialIndex}
		location={getRouteLabel()}
		on:close={closeImageModal}
	/>
{/if}

{#if !transportation && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if transportation}
	{#if data.user?.uuid && transportation.user && data.user.uuid === transportation.user}
		<div class="fixed bottom-6 right-6 z-50">
			<button
				class="btn btn-primary btn-circle w-16 h-16 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-110"
				on:click={() => (isEditModalOpen = true)}
			>
				<ClipboardList class="w-8 h-8" />
			</button>
		</div>
	{/if}

	<!-- Hero Section -->
	<div class="relative">
		<div
			class="hero min-h-[60vh] relative overflow-hidden"
			class:min-h-[30vh]={!transportation.images || transportation.images.length === 0}
		>
			<!-- Background: Images or Gradient -->
			{#if transportation.images && transportation.images.length > 0}
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each transportation.images as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							on:click={() => openImageModal(i)}
							aria-label={`View full image of ${transportation.name}`}
						>
							<img src={image.image} class="w-full h-full object-cover" alt={transportation.name} />
						</button>
					</div>
				{/each}
			{:else}
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			{/if}

			<!-- Content -->
			<div
				class="hero-content relative z-10 text-center"
				class:text-white={transportation.images?.length > 0}
			>
				<div class="max-w-4xl">
					<div class="flex justify-center items-center gap-3 mb-4">
						<span class="text-5xl">{getTransportationIcon(transportation.type)}</span>
						<h1 class="text-6xl font-bold drop-shadow-lg">{transportation.name}</h1>
					</div>

					<!-- Rating -->
					{#if transportation.rating !== undefined && transportation.rating !== null}
						<div class="flex justify-center mb-6">
							<div class="rating rating-lg">
								{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
									<input
										type="radio"
										name="rating-hero"
										class="mask mask-star-2 bg-warning"
										checked={star <= transportation.rating}
										disabled
									/>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Quick Info Badges -->
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						{#if transportation.type}
							<div class="badge badge-lg badge-primary font-semibold px-4 py-3">
								{$t(`transportation.modes.${transportation.type}`)}
							</div>
						{/if}
						{#if transportation.from_location}
							<div class="badge badge-lg badge-secondary font-semibold px-4 py-3">
								🚩 {transportation.from_location}
							</div>
						{/if}
						{#if transportation.to_location}
							<div class="badge badge-lg badge-secondary font-semibold px-4 py-3">
								🏁 {transportation.to_location}
							</div>
						{/if}
						{#if transportation.is_public}
							<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
								👁️ {$t('adventures.public')}
							</div>
						{:else}
							<div class="badge badge-lg badge-ghost font-semibold px-4 py-3">
								🔒 {$t('adventures.private')}
							</div>
						{/if}
					</div>

					<!-- Image Navigation (only shown when multiple images exist) -->
					{#if transportation.images && transportation.images.length > 1}
						<div class="w-full max-w-md mx-auto">
							<!-- Navigation arrows and current position -->
							<div class="flex items-center justify-center gap-4 mb-3">
								<button
									on:click={() =>
										goToSlide(
											currentSlide > 0 ? currentSlide - 1 : transportation.images.length - 1
										)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.previous_image')}
								>
									❮
								</button>

								<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
									{currentSlide + 1} / {transportation.images.length}
								</div>

								<button
									on:click={() =>
										goToSlide(
											currentSlide < transportation.images.length - 1 ? currentSlide + 1 : 0
										)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.next_image')}
								>
									❯
								</button>
							</div>

							<!-- Dot navigation -->
							{#if transportation.images.length <= 12}
								<div class="flex justify-center gap-2 flex-wrap">
									{#each transportation.images as _, i}
										<button
											on:click={() => goToSlide(i)}
											class="btn btn-circle btn-xs transition-all duration-200"
											class:btn-primary={i === currentSlide}
											class:btn-outline={i !== currentSlide}
											class:opacity-50={i !== currentSlide}
										>
											{i + 1}
										</button>
									{/each}
								</div>
							{:else}
								<div class="relative">
									<div
										class="absolute left-0 top-0 bottom-2 w-4 bg-gradient-to-r from-black/30 to-transparent pointer-events-none"
									></div>
									<div
										class="absolute right-0 top-0 bottom-2 w-4 bg-gradient-to-l from-black/30 to-transparent pointer-events-none"
									></div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-2 space-y-6 sm:space-y-8">
				<!-- Description Card -->
				{#if transportation.description}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 {$t('adventures.description')}</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(transportation.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- Map Section -->
				{#if mapCenter}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.location')}</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<MapLibre
									style={getBasemapUrl()}
									class="w-full h-96"
									standardControls
									center={mapCenter}
									zoom={13}
								>
									{#if hasOriginCoordinates(transportation)}
										<DefaultMarker
											lngLat={[
												Number(transportation.origin_longitude),
												Number(transportation.origin_latitude)
											]}
										>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{transportation.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{$t('transportation.from_location')}
														{getTransportationIcon(transportation.type)}
													</p>
													{#if transportation.rating}
														<div class="flex items-center gap-1 mb-2">
															{#each renderStars(transportation.rating) as filled}
																{#if filled}
																	<Star class="w-4 h-4 text-warning fill-current" />
																{:else}
																	<StarOutline class="w-4 h-4 text-gray-400" />
																{/if}
															{/each}
															<span class="text-xs text-black ml-1">
																({transportation.rating}/5)
															</span>
														</div>
													{/if}
													{#if transportation.from_location}
														<div class="text-xs text-black">
															📍 {transportation.from_location}
														</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}

									{#if hasDestinationCoordinates(transportation)}
										<DefaultMarker
											lngLat={[
												Number(transportation.destination_longitude),
												Number(transportation.destination_latitude)
											]}
										>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{transportation.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{$t('transportation.to_location')}
														{getTransportationIcon(transportation.type)}
													</p>
													{#if transportation.rating}
														<div class="flex items-center gap-1 mb-2">
															{#each renderStars(transportation.rating) as filled}
																{#if filled}
																	<Star class="w-4 h-4 text-warning fill-current" />
																{:else}
																	<StarOutline class="w-4 h-4 text-gray-400" />
																{/if}
															{/each}
															<span class="text-xs text-black ml-1">
																({transportation.rating}/5)
															</span>
														</div>
													{/if}
													{#if transportation.to_location}
														<div class="text-xs text-black">
															📍 {transportation.to_location}
														</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}
								</MapLibre>
							</div>
							{#if transportation.from_location || transportation.to_location}
								<p class="mt-4 text-base-content/70 flex items-center gap-2">
									<MapMarker class="w-5 h-5" />
									{getRouteLabel()}
								</p>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<!-- Quick Info Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h2 class="card-title text-xl mb-4">ℹ️ {$t('adventures.details')}</h2>
						<div class="space-y-4">
							<!-- Departure/Arrival -->
							{#if transportation.date || transportation.end_date}
								<div class="flex items-start gap-3">
									<CalendarRange class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">{$t('adventures.dates')}</p>
										<p class="text-base">
											{formatTravelWindow(
												transportation.date,
												transportation.end_date,
												transportation.start_timezone,
												transportation.end_timezone
											)}
										</p>
										{#if calculateDuration(transportation.date, transportation.end_date, transportation.start_timezone, transportation.end_timezone)}
											<p class="text-sm opacity-70 mt-1">
												{calculateDuration(
													transportation.date,
													transportation.end_date,
													transportation.start_timezone,
													transportation.end_timezone
												)}
											</p>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Type -->
							<div class="flex items-start gap-3">
								<span class="text-xl mt-1 flex-shrink-0"
									>{getTransportationIcon(transportation.type)}</span
								>
								<div>
									<p class="font-semibold text-sm opacity-70">{$t('transportation.type')}</p>
									<p class="text-base">{$t(`transportation.modes.${transportation.type}`)}</p>
								</div>
							</div>

							<!-- Flight Number -->
							{#if transportation.flight_number}
								<div class="flex items-start gap-3">
									<CardAccountDetails class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">
											{$t('transportation.flight_number')}
										</p>
										<p class="text-base font-mono">{transportation.flight_number}</p>
									</div>
								</div>
							{/if}

							<!-- Distance -->
							{#if transportation.distance}
								<div class="flex items-start gap-3">
									<CashMultiple class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div>
										<p class="font-semibold text-sm opacity-70">
											{$t('adventures.distance') ?? 'Distance'}
										</p>
										<p class="text-base">{transportation.distance} km</p>
									</div>
								</div>
							{/if}

							<!-- Link -->
							{#if transportation.link}
								<div class="flex items-start gap-3">
									<OpenInNew class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
									<div class="flex-1">
										<p class="font-semibold text-sm opacity-70 mb-1">{$t('adventures.link')}</p>
										<a
											href={transportation.link}
											target="_blank"
											rel="noopener noreferrer"
											class="link link-primary text-base break-all"
										>
											{transportation.link}
										</a>
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Additional Images -->
				{#if transportation.images && transportation.images.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-xl mb-4">🖼️ {$t('adventures.images')}</h2>
							<div class="grid grid-cols-2 gap-2">
								{#each transportation.images as image, i}
									<button
										class="aspect-square rounded-lg overflow-hidden hover:opacity-80 transition-opacity"
										on:click={() => openImageModal(i)}
									>
										<img
											src={image.image}
											alt={`${transportation.name} - ${i + 1}`}
											class="w-full h-full object-cover"
										/>
									</button>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Attachments -->
				{#if transportation.attachments && transportation.attachments.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-xl mb-4">📎 {$t('adventures.attachments')}</h2>
							<div class="space-y-2">
								{#each transportation.attachments as attachment}
									<AttachmentCard {attachment} />
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<svelte:head>
	<title>
		{data.props.transportation && data.props.transportation.name
			? `${data.props.transportation.name}`
			: 'Transportation'}
	</title>
	<meta name="description" content="View transportation details" />
</svelte:head>
