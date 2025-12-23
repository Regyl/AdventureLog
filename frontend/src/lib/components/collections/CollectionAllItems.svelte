<script lang="ts">
	import type { Collection } from '$lib/types';
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import LodgingCard from '$lib/components/cards/LodgingCard.svelte';
	import NoteCard from '$lib/components/cards/NoteCard.svelte';
	import ChecklistCard from '$lib/components/cards/ChecklistCard.svelte';
	import Magnify from '~icons/mdi/magnify';
	import ClipboardList from '~icons/mdi/clipboard-list';

	export let collection: Collection;
	export let user: any;
	export let isFolderView: boolean = false;

	// Whether the current user can modify this collection (owner or shared user)
	export let canModify: boolean = false;

	// Exported so a parent can bind to them if desired
	export let locationSearch: string = '';
	export let locationSort:
		| 'alphabetical-asc'
		| 'alphabetical-desc'
		| 'visited'
		| 'date-asc'
		| 'date-desc' = 'alphabetical-asc';

	$: sortedLocations = (() => {
		if (!collection?.locations) return [];

		let filtered = collection.locations.filter(
			(loc) =>
				loc.name.toLowerCase().includes(locationSearch.toLowerCase()) ||
				loc.location?.toLowerCase().includes(locationSearch.toLowerCase())
		);

		switch (locationSort) {
			case 'alphabetical-asc':
				return filtered.sort((a, b) => a.name.localeCompare(b.name));
			case 'alphabetical-desc':
				return filtered.sort((a, b) => b.name.localeCompare(a.name));
			case 'visited':
				return filtered.sort((a, b) => {
					const aVisited = a.visits && a.visits.length > 0 ? 1 : 0;
					const bVisited = b.visits && b.visits.length > 0 ? 1 : 0;
					return bVisited - aVisited;
				});
			case 'date-asc':
				return filtered.sort((a, b) => {
					const aDate = a.visits?.[0]?.start_date || '';
					const bDate = b.visits?.[0]?.start_date || '';
					return aDate.localeCompare(bDate);
				});
			case 'date-desc':
				return filtered.sort((a, b) => {
					const aDate = a.visits?.[0]?.start_date || '';
					const bDate = b.visits?.[0]?.start_date || '';
					return bDate.localeCompare(aDate);
				});
			default:
				return filtered;
		}
	})();

	// Transportations
	export let transportationSearch: string = '';
	$: filteredTransportations = (() => {
		if (!collection?.transportations) return [];
		return collection.transportations.filter((t) =>
			t.name.toLowerCase().includes(transportationSearch.toLowerCase())
		);
	})();

	// Lodging
	export let lodgingSearch: string = '';
	$: filteredLodging = (() => {
		if (!collection?.lodging) return [];
		return collection.lodging.filter((l) =>
			l.name.toLowerCase().includes(lodgingSearch.toLowerCase())
		);
	})();

	// Notes
	export let noteSearch: string = '';
	$: filteredNotes = (() => {
		if (!collection?.notes) return [];
		return collection.notes.filter((n) => n.name.toLowerCase().includes(noteSearch.toLowerCase()));
	})();

	// Checklists
	export let checklistSearch: string = '';
	$: filteredChecklists = (() => {
		if (!collection?.checklists) return [];
		return collection.checklists.filter((c) =>
			c.name.toLowerCase().includes(checklistSearch.toLowerCase())
		);
	})();
</script>

{#if collection.locations && collection.locations.length > 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
				<h2 class="card-title text-2xl">
					📍 Locations ({sortedLocations.length}/{collection.locations.length})
				</h2>

				{#if isFolderView}
					<div class="flex flex-wrap gap-2">
						<!-- Search -->
						<div class="join">
							<input
								type="text"
								placeholder="Search locations..."
								class="input input-sm input-bordered join-item w-48"
								bind:value={locationSearch}
							/>
						</div>

						<!-- Sort dropdown -->
						<select class="select select-sm select-bordered" bind:value={locationSort}>
							<option value="alphabetical-asc">A → Z</option>
							<option value="alphabetical-desc">Z → A</option>
							<option value="visited">Visited First</option>
							<option value="date-asc">Oldest First</option>
							<option value="date-desc">Newest First</option>
						</select>
					</div>
				{/if}
			</div>

			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch">
				{#each sortedLocations as location}
					<LocationCard adventure={location} {user} {collection} />
				{/each}
			</div>

			{#if sortedLocations.length === 0}
				<div class="text-center py-8 opacity-70">
					<p>No locations match your search</p>
				</div>
			{/if}

			<!-- Transportations Section -->
			{#if collection.transportations && collection.transportations.length > 0}
				<div class="card bg-base-200 shadow-xl mt-6">
					<div class="card-body">
						<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
							<h2 class="card-title text-2xl">
								✈️ Transportation ({filteredTransportations.length}/{collection.transportations
									.length})
							</h2>

							{#if isFolderView}
								<div class="join">
									<input
										type="text"
										placeholder="Search transportation..."
										class="input input-sm input-bordered join-item w-48"
										bind:value={transportationSearch}
									/>
									<button class="btn btn-sm btn-square join-item">
										<Magnify class="w-4 h-4" />
									</button>
								</div>
							{/if}
						</div>

						<div
							class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
						>
							{#each filteredTransportations as transport}
								<TransportationCard transportation={transport} {user} {collection} />
							{/each}
						</div>

						{#if filteredTransportations.length === 0}
							<div class="text-center py-8 opacity-70">
								<p>No transportation matches your search</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Lodging Section -->
			{#if collection.lodging && collection.lodging.length > 0}
				<div class="card bg-base-200 shadow-xl mt-6">
					<div class="card-body">
						<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
							<h2 class="card-title text-2xl">
								🏨 Lodging ({filteredLodging.length}/{collection.lodging.length})
							</h2>

							{#if isFolderView}
								<div class="join">
									<input
										type="text"
										placeholder="Search lodging..."
										class="input input-sm input-bordered join-item w-48"
										bind:value={lodgingSearch}
									/>
									<button class="btn btn-sm btn-square join-item">
										<Magnify class="w-4 h-4" />
									</button>
								</div>
							{/if}
						</div>

						<div
							class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
						>
							{#each filteredLodging as lodging}
								<LodgingCard {lodging} {user} {collection} />
							{/each}
						</div>

						{#if filteredLodging.length === 0}
							<div class="text-center py-8 opacity-70">
								<p>No lodging matches your search</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Notes Section -->
			{#if collection.notes && collection.notes.length > 0}
				<div class="card bg-base-200 shadow-xl mt-6">
					<div class="card-body">
						<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
							<h2 class="card-title text-2xl">
								📝 Notes ({filteredNotes.length}/{collection.notes.length})
							</h2>

							{#if isFolderView}
								<div class="join">
									<input
										type="text"
										placeholder="Search notes..."
										class="input input-sm input-bordered join-item w-48"
										bind:value={noteSearch}
									/>
									<button class="btn btn-sm btn-square join-item">
										<Magnify class="w-4 h-4" />
									</button>
								</div>
							{/if}
						</div>

						<div
							class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
						>
							{#each filteredNotes as note}
								<NoteCard {note} {user} {collection} />
							{/each}
						</div>

						{#if filteredNotes.length === 0}
							<div class="text-center py-8 opacity-70">
								<p>No notes match your search</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Checklists Section -->
			{#if collection.checklists && collection.checklists.length > 0}
				<div class="card bg-base-200 shadow-xl mt-6">
					<div class="card-body">
						<div class="flex flex-wrap justify-between items-center gap-4 mb-6">
							<h2 class="card-title text-2xl">
								<ClipboardList class="w-6 h-6" />
								Checklists ({filteredChecklists.length}/{collection.checklists.length})
							</h2>

							{#if isFolderView}
								<div class="join">
									<input
										type="text"
										placeholder="Search checklists..."
										class="input input-sm input-bordered join-item w-48"
										bind:value={checklistSearch}
									/>
									<button class="btn btn-sm btn-square join-item">
										<Magnify class="w-4 h-4" />
									</button>
								</div>
							{/if}
						</div>

						<div
							class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-fr items-stretch"
						>
							{#each filteredChecklists as checklist}
								<ChecklistCard {checklist} {user} {collection} />
							{/each}
						</div>

						{#if filteredChecklists.length === 0}
							<div class="text-center py-8 opacity-70">
								<p>No checklists match your search</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
