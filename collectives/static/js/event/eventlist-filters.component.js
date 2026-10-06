import { searchLeaders } from "../api.js";

const { ref, inject, reactive, computed } = Vue

/** Un critère est actif s'il porte une valeur (liste non vide, texte, date, booléen vrai). */
const isSet = (value) => (Array.isArray(value) ? value.length > 0 : Boolean(value))

export default {

  props: ["filters"],
  components: {
  },

  setup (props) {
    const config = inject('config')

    const leadersSearch = reactive({
      loading: false,
      results: []
    })

    const fetchLeaders = async ({ query: leaderQueryName }) => {
        if(!leaderQueryName) return
        leadersSearch.loading = true
        const { data } = await searchLeaders(leaderQueryName)
        leadersSearch.results = data.map(res => res.full_name)
        leadersSearch.loading = false
    }
    const removeFilterElement = (filterList, element) => {
      if (!filterList) return filterList;
      return filterList.filter(id => id !== element);
    }

    const getActivityIcon = (activityId) => {
      var iconName = activityId == "__services" ? "benevolat" : activityId;
      return `/static/caf/icon/${iconName}.svg`
    };

    // Les filtres sont conservés en localStorage sans date d'expiration: un critère
    // retiré côté serveur depuis la dernière visite y subsiste. Le rendu de son chip
    // échoue alors, et c'est le filtre entier qui disparait de la barre.
    const pruneUnknown = (selected, options) =>
      (selected || []).filter(id => options.some(option => option.id === id))

    props.filters.activities = pruneUnknown(props.filters.activities, config.activityList)
    props.filters.eventTypes = pruneUnknown(props.filters.eventTypes, config.eventTypes)
    props.filters.eventTags = pruneUnknown(props.filters.eventTags, config.eventTags)

    /** Critères masqués tant que « Plus de filtres » n'est pas déplié. */
    const advancedFilters = () => [
      props.filters.eventTypes,
      props.filters.eventTags,
      props.filters.date,
      props.filters.title,
      props.filters.leader,
      props.filters.displayCancelled,
    ]

    const advancedFilterCount = computed(() => advancedFilters().filter(isSet).length)
    const activeFilterCount = computed(
      () => advancedFilterCount.value + (isSet(props.filters.activities) ? 1 : 0)
    )

    // Les filtres sont restaurés du localStorage d'une visite à l'autre. Si l'un des
    // critères avancés est actif, on déplie le panneau: sinon la liste s'affiche
    // filtrée sans que rien à l'écran ne l'explique.
    const displayMoreFilters = ref(advancedFilterCount.value > 0)

    const resetFilters = () => Object.assign(props.filters, {
      activities: [],
      eventTypes: [],
      eventTags: [],
      date: null,
      title: null,
      leader: null,
      displayCancelled: false,
    })

    return {
      displayMoreFilters,
      filters: props.filters,
      config,
      advancedFilterCount,
      activeFilterCount,
      resetFilters,
      toggleMoreFilters: () => displayMoreFilters.value = !displayMoreFilters.value,
      toggleCancelled: () => props.filters.displayCancelled = !props.filters.displayCancelled,
      findInConfig: (list, activityId) => list.find(id =>  id.id === activityId),
      fetchLeaders,
      leadersSearch,
      removeFilterElement,
      getActivityIcon
    }
  },
  template: `
  <search class="collectives-list-filters" role="search" aria-label="Filtrer les collectives">
    <p-multiselect 
      class="select-activity w-full sm:w-100>" 
      v-model="filters.activities" 
      display="chip" 
      :options="config.activityList" 
      optionLabel="name" 
      optionValue="id"
      appendTo="self"
      :showToggleAll="false"
      scrollHeight="90vh"
      placeholder="Toutes activités"
      ariaLabel="Filtrer par activité"
    >
      <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="getActivityIcon(slotProps.option.id)" />
              <div>{{ slotProps.option.name }}</div>
          </div>
      </template>
      <template #chip="slotProps">
          <Chip :label="findInConfig(config.activityList, slotProps.value).name" :image="getActivityIcon(slotProps.value)" removable @remove="filters.activities = removeFilterElement(filters.activities, slotProps.value)"/>
      </template>
      <template #footer="slotProps">
        <div class="flex justify-between" v-if="slotProps.value?.length > 0">
            <div></div>
            <Button label="Effacer" severity="danger" text size="small" icon="pi pi-times" @click="filters.activities = []" />
        </div>
      </template>
    </p-multiselect>

    <button
      type="button"
      class="toggle-button collectives-list-filters-toggle-label button-primary"
      @click="toggleMoreFilters"
      :aria-expanded="displayMoreFilters"
    >
      <span v-if="!displayMoreFilters">+ Plus de filtres</span>
      <span v-else>&minus; Moins de filtres</span>
      <span
        v-if="!displayMoreFilters && advancedFilterCount > 0"
        class="filter-badge"
      >{{ advancedFilterCount }}<span class="visually-hidden"> filtre(s) masqué(s) actif(s)</span></span>
    </button>

    <template v-if="displayMoreFilters">

      <p-multiselect 
        class="select-type"
        v-model="filters.eventTypes" 
        :options="config.eventTypes" 
        optionLabel="name" 
        optionValue="id"
        scrollHeight="90vh"
        placeholder="Tout types d'événement"
        display="chip" 
        appendTo="self"
        :showToggleAll="false"
        ariaLabel="Filtrer par type d'événement"
      >
        <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="'/static/caf/icon/' + slotProps.option.id + '.svg'" />
              <div>{{ slotProps.option.name }}</div>
          </div>
        </template>
        <template #chip="slotProps">
            <Chip :label="findInConfig(config.eventTypes, slotProps.value).name" :image="'/static/caf/icon/' + slotProps.value + '.svg'" removable @remove="filters.eventTypes = removeFilterElement(filters.eventTypes, slotProps.value)" />
        </template>
        <template #footer="slotProps">
          <div class="flex justify-between" v-if="slotProps.value?.length > 0">
              <div></div>
              <Button label="Effacer" severity="danger" text size="small" icon="pi pi-times" @click="filters.eventTypes = []" />
          </div>
        </template>
      </p-multiselect>

      <p-multiselect 
        class="select-tag"
        v-model="filters.eventTags" 
        :options="config.eventTags" 
        optionLabel="name" 
        optionValue="id"
        scrollHeight="90vh"
        placeholder="Tous labels"
        display="chip" 
        appendTo="self"
        :showToggleAll="false"
        ariaLabel="Filtrer par label"
      >
        <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="'/static/caf/icon/' + slotProps.option.id + '.svg'" />
              <div>{{ slotProps.option.name }}</div>
          </div>
        </template>
        <template #chip="slotProps">
            <Chip :label="findInConfig(config.eventTags, slotProps.value).name" :image="'/static/caf/icon/' + slotProps.value + '.svg'" removable @remove="filters.eventTags = removeFilterElement(filters.eventTags, slotProps.value)" />
        </template>
        <template #footer="slotProps">
          <div class="flex justify-between" v-if="slotProps.value?.length > 0">
              <div></div>
              <Button label="Effacer" severity="danger" text size="small" icon="pi pi-times" @click="filters.eventTags = []" />
          </div>
        </template>
      </p-multiselect>

      <div class="input date">
        <label class="borders" for="filter-date">
          <i class="pi pi-calendar" aria-hidden="true"></i>
          Depuis
          <p-datepicker 
            inputId="filter-date"
            dateFormat="dd/mm/yy"
            v-model="filters.date"
            placeholder="Aujourd'hui"
          ></p-datepicker>
        </label>
      </div>

      <label class="borders" for="filter-title">
        <i class="pi pi-search" aria-hidden="true"></i>
        <span class="visually-hidden">Titre de la collective</span>
        <input id="filter-title" type="text" v-model="filters.title" placeholder="Titre">
      </label>

      <AutoComplete 
        inputId="filter-leader" 
        v-model="filters.leader" 
        :suggestions="leadersSearch.results" 
        :loading="leadersSearch.loading"
        @complete="fetchLeaders" 
        placeholder="Encadrant"
        ariaLabel="Rechercher un encadrant"
      />

      <button
        type="button"
        id="cancelled"
        class="toggle-button font-size-s"
        @click="toggleCancelled"
        :class="{ enabled: filters.displayCancelled }"
        :aria-pressed="filters.displayCancelled"
      >
        Sorties annulées :
        <span v-if="filters.displayCancelled" class="icon-button display-for-on">affichées <img src="/static/img/icon/ionicon/eye.svg" alt=""/></span>
        <span v-if="!filters.displayCancelled" class="icon-button display-for-off">cachées <img src="/static/img/icon/ionicon/eye-off.svg" alt=""/></span>
      </button>

    </template>

    <button
      type="button"
      v-if="activeFilterCount > 0"
      class="toggle-button font-size-s reset-filters"
      @click="resetFilters"
    >
      <i class="pi pi-times" aria-hidden="true"></i>
      Tout effacer<span class="visually-hidden"> les filtres</span>
    </button>
  </search>
  `
}
