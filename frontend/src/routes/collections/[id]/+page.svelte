<script lang="ts">
	import type { Collection, ContentImage, Location } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import { DateTime } from 'luxon';
	import Calendar from '~icons/mdi/calendar';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import CollectionAllItems from '$lib/components/collections/CollectionAllItems.svelte';
	import CollectionItineraryPlanner from '$lib/components/collections/CollectionItineraryPlanner.svelte';
	import CollectionRecommendationView from '$lib/components/CollectionRecommendationView.svelte';
	import LocationLink from '$lib/components/LocationLink.svelte';
	import { getBasemapUrl } from '$lib';
	import FolderMultiple from '~icons/mdi/folder-multiple';
	import FormatListBulleted from '~icons/mdi/format-list-bulleted';
	import Timeline from '~icons/mdi/timeline';
	import Map from '~icons/mdi/map';
	import Lightbulb from '~icons/mdi/lightbulb';
	import Plus from '~icons/mdi/plus';
	import { addToast } from '$lib/toasts';

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	export let data: PageData;

	// Handle both 'collection' and 'adventure' properties for backward compatibility
	let collection: Collection = (data.props as any).collection || (data.props as any).adventure;
	let currentSlide = 0;
	let notFound: boolean = false;
	let isEditModalOpen: boolean = false;
	let heroImages: ContentImage[] = [];
	let modalInitialIndex: number = 0;
	let isImageModalOpen: boolean = false;
	let isLocationLinkModalOpen: boolean = false;

	// View state from URL params
	type ViewType = 'all' | 'itinerary' | 'map' | 'recommendations';
	let currentView: ViewType = 'itinerary';

	// Determine if this is a folder view (no dates) or itinerary view (has dates)
	$: isFolderView = !collection?.start_date && !collection?.end_date;

	// Gather all images from locations for the hero
	$: heroImages = collection?.locations?.flatMap((loc) => loc.images || []) || [];

	// Define available views based on collection type
	$: availableViews = {
		all: true, // Always available
		itinerary: !isFolderView, // Only for collections with dates
		map: collection?.locations?.some((l) => l.latitude && l.longitude) || false,
		recommendations: true // may be overridden by permission check below
	};

	// Get default view based on available views
	let defaultView: ViewType;
	$: defaultView = (availableViews.itinerary ? 'itinerary' : 'all') as ViewType;

	// Read view from URL params and validate it's available
	$: {
		const view = $page.url.searchParams.get('view') as ViewType;
		if (
			view &&
			['all', 'itinerary', 'map', 'recommendations'].includes(view) &&
			availableViews[view]
		) {
			currentView = view;
		} else {
			currentView = defaultView;
		}
	}

	// Determine whether current user can modify the collection (owner or shared user)
	$: canModifyCollection = (() => {
		const u = data.user as any;
		if (!u || !collection) return false;

		const userUuid = u.uuid || null;
		const username = u.username || null;
		const pk = u.pk !== undefined && u.pk !== null ? String(u.pk) : null;
		const owner = collection.user;

		// Direct matches: UUID (primary), username, or numeric pk (stringified)
		if (userUuid && owner === userUuid) return true;
		if (username && owner === username) return true;
		if (pk && owner === pk) return true;

		// Shared with may contain UUIDs or other identifiers
		if (collection.shared_with && Array.isArray(collection.shared_with)) {
			if (userUuid && collection.shared_with.includes(userUuid)) return true;
			if (username && collection.shared_with.includes(username)) return true;
			if (pk && collection.shared_with.includes(pk)) return true;
		}

		return false;
	})();

	// Enforce recommendations visibility only for owner/shared users
	$: availableViews.recommendations = !!canModifyCollection;

	onMount(async () => {
		if (!collection) {
			notFound = true;
		}
	});

	function goToSlide(index: number) {
		currentSlide = index;
	}

	function closeImageModal() {
		isImageModalOpen = false;
	}

	function openImageModal(imageIndex: number) {
		modalInitialIndex = imageIndex;
		isImageModalOpen = true;
	}

	function formatDate(dateString: string | null) {
		if (!dateString) return '';
		return DateTime.fromISO(dateString).toLocaleString(DateTime.DATE_MED);
	}

	function getMapCenter() {
		if (collection.locations && collection.locations.length > 0) {
			const firstLocation = collection.locations.find((l) => l.latitude && l.longitude);
			if (firstLocation) {
				return { lng: firstLocation.longitude!, lat: firstLocation.latitude! };
			}
		}
		return { lng: 0, lat: 0 };
	}

	function switchView(view: ViewType) {
		const url = new URL($page.url);
		url.searchParams.set('view', view);
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	function openLocationLinkModal() {
		isLocationLinkModalOpen = true;
	}

	function closeLocationLinkModal() {
		isLocationLinkModalOpen = false;
	}

	async function handleLocationAdded(event: CustomEvent<Location>) {
		// Link the location to this collection
		const location = event.detail;

		try {
			const response = await fetch(`/api/locations/${location.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					collections: [...(location.collections || []), collection.id]
				})
			});

			if (response.ok) {
				// Keep modal open so user can link more locations.
				// Update local collection state so UI reflects the new link immediately.
				try {
					if (!collection.locations) collection.locations = [];
					// Avoid duplicates
					const exists = collection.locations.some((l) => String(l.id) === String(location.id));
					if (!exists) {
						collection.locations = [...collection.locations, location];
					}
				} catch (e) {
					// if collection shape is unexpected, ignore and continue
					console.warn('Unable to update local collection.locations', e);
				}

				// Show success message but do NOT close the modal or reload the page
				addToast(
					'success',
					$t('adventures.collection_link_location_success') || 'Location added successfully'
				);
			} else {
				addToast(
					'error',
					$t('adventures.collection_link_location_error') || 'Failed to add location'
				);
			}
		} catch (error) {
			console.error('Error linking location:', error);
			addToast(
				'error',
				$t('adventures.collection_link_location_error') || 'Failed to add location'
			);
		}
	}
</script>

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('collections.not_found')}</h1>
				<p class="text-lg opacity-70 mb-8">{$t('collections.not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isImageModalOpen}
	<ImageDisplayModal
		images={heroImages}
		initialIndex={modalInitialIndex}
		name={collection.name}
		on:close={closeImageModal}
	/>
{/if}

{#if isLocationLinkModalOpen && collection}
	<LocationLink
		user={data.user}
		collectionId={collection.id}
		on:close={closeLocationLinkModal}
		on:add={handleLocationAdded}
	/>
{/if}

{#if !collection && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if collection}
	<!-- Hero Section -->
	<div class="relative">
		<div
			class="hero min-h-[60vh] relative overflow-hidden"
			class:min-h-[30vh]={!heroImages || heroImages.length === 0}
		>
			<!-- Background: Images or Gradient -->
			{#if heroImages && heroImages.length > 0}
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each heroImages as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							on:click={() => openImageModal(i)}
							aria-label={`View full image of ${collection.name}`}
						>
							<img src={image.image} class="w-full h-full object-cover" alt={collection.name} />
						</button>
					</div>
				{/each}
			{:else}
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			{/if}

			<!-- Content -->
			<div class="hero-content relative z-10 text-center" class:text-white={heroImages?.length > 0}>
				<div class="max-w-4xl">
					<h1 class="text-6xl font-bold mb-4 drop-shadow-lg flex items-center justify-center gap-4">
						{#if isFolderView}
							<FolderMultiple class="w-16 h-16" />
						{/if}
						{collection.name}
					</h1>

					<!-- Quick Info Badges -->
					<div class="flex flex-wrap justify-center gap-4 mb-6">
						{#if collection.is_public}
							<div class="badge badge-lg badge-success font-semibold px-4 py-3">
								🌍 {$t('adventures.public')}
							</div>
						{:else}
							<div class="badge badge-lg badge-warning font-semibold px-4 py-3">
								🔒 {$t('adventures.private')}
							</div>
						{/if}
						{#if collection.locations && collection.locations.length > 0}
							<div class="badge badge-lg badge-primary font-semibold px-4 py-3">
								📍 {collection.locations.length}
								{collection.locations.length === 1 ? 'Location' : 'Locations'}
							</div>
						{/if}
						{#if collection.start_date || collection.end_date}
							<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
								<Calendar class="w-5 h-5 mr-1" />
								{#if collection.start_date && collection.end_date}
									{formatDate(collection.start_date)} - {formatDate(collection.end_date)}
								{:else if collection.start_date}
									From {formatDate(collection.start_date)}
								{:else if collection.end_date}
									Until {formatDate(collection.end_date)}
								{/if}
							</div>
						{/if}
						{#if collection.is_archived}
							<div class="badge badge-lg badge-neutral font-semibold px-4 py-3">📦 Archived</div>
						{/if}
					</div>

					<!-- Image Navigation (only shown when multiple images exist) -->
					{#if heroImages && heroImages.length > 1}
						<div class="w-full max-w-md mx-auto">
							<!-- Navigation arrows and current position -->
							<div class="flex items-center justify-center gap-4 mb-3">
								<button
									on:click={() =>
										goToSlide(currentSlide > 0 ? currentSlide - 1 : heroImages.length - 1)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.previous_image')}
								>
									❮
								</button>

								<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
									{currentSlide + 1} / {heroImages.length}
								</div>

								<button
									on:click={() =>
										goToSlide(currentSlide < heroImages.length - 1 ? currentSlide + 1 : 0)}
									class="btn btn-circle btn-sm btn-primary"
									aria-label={$t('adventures.next_image')}
								>
									❯
								</button>
							</div>

							<!-- Dot navigation -->
							{#if heroImages.length <= 12}
								<div class="flex justify-center gap-2 flex-wrap">
									{#each heroImages as _, i}
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
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<!-- View Switcher -->
		<div class="flex justify-center mb-6">
			<div class="join">
				{#if availableViews.all}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'all'}
						on:click={() => switchView('all')}
					>
						<FormatListBulleted class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">All Items</span>
					</button>
				{/if}
				{#if availableViews.itinerary}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'itinerary'}
						on:click={() => switchView('itinerary')}
					>
						<Timeline class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">Itinerary</span>
					</button>
				{/if}
				{#if availableViews.map}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'map'}
						on:click={() => switchView('map')}
					>
						<Map class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">Map</span>
					</button>
				{/if}
				{#if availableViews.recommendations}
					<button
						class="btn join-item"
						class:btn-active={currentView === 'recommendations'}
						on:click={() => switchView('recommendations')}
					>
						<Lightbulb class="w-5 h-5 sm:mr-2" aria-hidden="true" />
						<span class="hidden sm:inline">Recommendations</span>
					</button>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-4 gap-6 sm:gap-10">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-3 space-y-8 sm:space-y-10">
				<!-- Description Card (always visible) -->
				{#if collection.description}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 Description</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(collection.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- All Items View -->
				{#if currentView === 'all' && collection.locations && collection.locations.length > 0}
					<CollectionAllItems
						{collection}
						user={data.user}
						{isFolderView}
						canModify={canModifyCollection}
					/>
				{/if}

				<!-- Itinerary View -->
				{#if currentView === 'itinerary'}
					<CollectionItineraryPlanner
						{collection}
						user={data.user}
						canModify={canModifyCollection}
					/>
				{/if}

				<!-- Map View -->
				{#if currentView === 'map' && collection.locations && collection.locations.some((l) => l.latitude && l.longitude)}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ Map</h2>
							<div class="rounded-lg overflow-hidden shadow-lg">
								<MapLibre
									style={getBasemapUrl()}
									class="w-full h-full min-h-[600px]"
									standardControls
									center={getMapCenter()}
									zoom={8}
								>
									{#each collection.locations as location}
										{#if location.latitude && location.longitude}
											<DefaultMarker lngLat={{ lng: location.longitude, lat: location.latitude }}>
												<Popup openOn="click" offset={[0, -10]}>
													<div class="p-2">
														<a
															href={`/adventures/${location.id}`}
															class="text-lg font-bold text-black hover:underline mb-1 block"
														>
															{location.name}
														</a>
														{#if location.category}
															<p class="font-semibold text-black text-sm mb-2">
																{location.category.display_name}
																{location.category.icon}
															</p>
														{/if}
														{#if location.location}
															<p class="text-xs text-black opacity-70">📍 {location.location}</p>
														{/if}
													</div>
												</Popup>
											</DefaultMarker>
										{/if}
									{/each}
								</MapLibre>
							</div>
						</div>
					</div>
				{/if}

				<!-- Recommendations View -->
				{#if currentView === 'recommendations'}
					<CollectionRecommendationView
						{collection}
						user={data.user}
						canModify={canModifyCollection}
					/>
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="lg:col-span-1 space-y-4 sm:space-y-6">
				<!-- Progress Tracker (only for folder views) -->
				{#if isFolderView && collection.locations && collection.locations.length > 0}
					{@const visitedCount = collection.locations.filter((l) => l.is_visited).length}
					{@const totalCount = collection.locations.length}
					{@const progressPercent = totalCount > 0 ? (visitedCount / totalCount) * 100 : 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">✅ Progress</h3>
							<div class="space-y-4">
								<div class="flex justify-between text-sm">
									<span class="opacity-70">Visited</span>
									<span class="font-bold">{visitedCount} / {totalCount}</span>
								</div>
								<div class="w-full bg-base-300 rounded-full h-4 overflow-hidden">
									<div
										class="bg-success h-full transition-all duration-500 rounded-full flex items-center justify-center text-xs font-bold text-success-content"
										style="width: {progressPercent}%"
									>
										{#if progressPercent > 20}
											{Math.round(progressPercent)}%
										{/if}
									</div>
								</div>
								{#if progressPercent < 20 && progressPercent > 0}
									<div class="text-center text-xs opacity-70">{Math.round(progressPercent)}%</div>
								{/if}
								<div class="grid grid-cols-2 gap-2 pt-2">
									<div class="stat bg-base-300 rounded-lg p-3">
										<div class="stat-title text-xs">Visited</div>
										<div class="stat-value text-lg text-success">{visitedCount}</div>
									</div>
									<div class="stat bg-base-300 rounded-lg p-3">
										<div class="stat-title text-xs">Planned</div>
										<div class="stat-value text-lg text-warning">{totalCount - visitedCount}</div>
									</div>
								</div>
								{#if visitedCount === totalCount && totalCount > 0}
									<div class="alert alert-success text-sm py-2">
										<span>🎉 All locations visited!</span>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Quick Info Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">ℹ️ {$t('adventures.basic_information')}</h3>
						<div class="space-y-3">
							{#if collection.start_date || collection.end_date}
								<div>
									<div class="text-sm opacity-70 mb-1">Dates</div>
									<div class="text-sm">
										{#if collection.start_date && collection.end_date}
											{formatDate(collection.start_date)} - {formatDate(collection.end_date)}
										{:else if collection.start_date}
											From {formatDate(collection.start_date)}
										{:else if collection.end_date}
											Until {formatDate(collection.end_date)}
										{/if}
									</div>
								</div>
							{/if}
							{#if collection.link}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.link')}</div>
									<a
										href={collection.link}
										class="link link-primary text-sm break-all"
										target="_blank"
									>
										{collection.link.length > 30
											? `${collection.link.slice(0, 30)}...`
											: collection.link}
									</a>
								</div>
							{/if}
							{#if collection.shared_with && collection.shared_with.length > 0}
								<div>
									<div class="text-sm opacity-70 mb-1">Shared With</div>
									<div class="flex flex-wrap gap-1">
										{#each collection.shared_with as username}
											<span class="badge badge-sm badge-outline">{username}</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Collection Stats Card -->
				<div class="card bg-base-200 shadow-xl">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">📊 Statistics</h3>
						<div class="stats stats-vertical shadow">
							{#if collection.locations}
								<div class="stat">
									<div class="stat-title">Locations</div>
									<div class="stat-value text-2xl">{collection.locations.length}</div>
								</div>
							{/if}
							{#if collection.transportations}
								<div class="stat">
									<div class="stat-title">Transportations</div>
									<div class="stat-value text-2xl">{collection.transportations.length}</div>
								</div>
							{/if}
							{#if collection.lodging}
								<div class="stat">
									<div class="stat-title">Lodging</div>
									<div class="stat-value text-2xl">{collection.lodging.length}</div>
								</div>
							{/if}
							{#if collection.notes}
								<div class="stat">
									<div class="stat-title">Notes</div>
									<div class="stat-value text-2xl">{collection.notes.length}</div>
								</div>
							{/if}
							{#if collection.checklists}
								<div class="stat">
									<div class="stat-title">Checklists</div>
									<div class="stat-value text-2xl">{collection.checklists.length}</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Additional Images (from locations) -->
				{#if heroImages && heroImages.length > 0}
					<div class="card bg-base-200 shadow-xl">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🖼️ {$t('adventures.images')}</h3>
							<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
								{#each heroImages.slice(0, 12) as image, index}
									<div class="relative group">
										<div
											class="aspect-square bg-cover bg-center rounded-lg cursor-pointer transition-transform duration-200 group-hover:scale-105"
											style="background-image: url({image.image})"
											on:click={() => openImageModal(index)}
											on:keydown={(e) => e.key === 'Enter' && openImageModal(index)}
											role="button"
											tabindex="0"
										></div>
										{#if image.is_primary}
											<div class="absolute top-1 right-1">
												<span class="badge badge-primary badge-xs">{$t('settings.primary')}</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
							{#if heroImages.length > 12}
								<div class="text-center mt-2 text-sm opacity-70">
									+{heroImages.length - 12} more {heroImages.length - 12 === 1 ? 'image' : 'images'}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Floating Action Button (FAB) - Only shown if user can modify collection -->
{#if collection && canModifyCollection}
	<div class="fixed bottom-6 right-6 z-40">
		<button
			class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
			on:click={openLocationLinkModal}
			aria-label="Add locations to collection"
		>
			<Plus class="w-8 h-8" />
		</button>
	</div>
{/if}

<svelte:head>
	<title>
		{collection && collection.name ? `${collection.name}` : 'Collection'}
	</title>
	<meta name="description" content="View collection details and locations" />
</svelte:head>
