import { searchLeaders } from "../api.js";

const { ref, inject, reactive } = Vue

export default {

  props: ["filters"],
  components: {
  },

  setup (props) {
    const displayMoreFilters = ref(false)
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

    return {
      displayMoreFilters,
      filters: props.filters,
      config,
      toggleCancelled: () => props.filters.displayCancelled = !props.filters.displayCancelled,
      findInConfig: (list, activityId) => list.find(id =>  id.id === activityId),
      fetchLeaders,
      leadersSearch,
    }
  },
  template: `
  <div class="collectives-list-filters">
    <p-multiselect 
      class="select-activity w-full sm:w-100>" 
      v-model="filters.activities" 
      display="chip" 
      :options="config.activityList" 
      optionLabel="name" 
      optionValue="id"
      filter 
      placeholder="Toutes activités"
    >
      <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="'/static/caf/icon/' + slotProps.option.id + '.svg'" />
              <div>{{ slotProps.option.name }}</div>
          </div>
      </template>
      <template #chip="slotProps">
          <Chip :label="findInConfig(config.activityList, slotProps.value).name" :image="'/static/caf/icon/' + slotProps.value + '.svg'" removable @remove="filters.activities = filters.activities.filter(id => id !== slotProps.value)"/>
      </template>
    </p-multiselect>

    <div 
      v-if="!displayMoreFilters"
      class="toggle-button collectives-list-filters-toggle-label button-primary"
      @click="displayMoreFilters = true"
    >
      + Plus de filtres
    </div>

    <template v-if="displayMoreFilters">

      <p-multiselect 
        class="select-type"
        v-model="filters.eventTypes" 
        :options="config.eventTypes" 
        optionLabel="name" 
        optionValue="id"
        placeholder="Tout types d'événement"
        display="chip" 
        filter 
      >
        <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="'/static/caf/icon/' + slotProps.option.id + '.svg'" />
              <div>{{ slotProps.option.name }}</div>
          </div>
        </template>
        <template #chip="slotProps">
            <Chip :label="findInConfig(config.eventTypes, slotProps.value).name" :image="'/static/caf/icon/' + slotProps.value + '.svg'" removable @remove="filters.eventTypes = filters.eventTypes.filter(id => id !== slotProps.value)" />
        </template>
      </p-multiselect>

      <p-multiselect 
        class="select-tag"
        v-model="filters.eventTags" 
        :options="config.eventTags" 
        optionLabel="name" 
        optionValue="id"
        placeholder="Tous labels"
        display="chip" 
        filter 
      >
        <template #option="slotProps">
          <div class="flex items-center">
              <img class="icon" :alt="slotProps.option.name" :src="'/static/caf/icon/' + slotProps.option.id + '.svg'" />
              <div>{{ slotProps.option.name }}</div>
          </div>
        </template>
        <template #chip="slotProps">
            <Chip :label="findInConfig(config.eventTags, slotProps.value).name" :image="'/static/caf/icon/' + slotProps.value + '.svg'" removable @remove="filters.eventTags = filters.eventTags.filter(id => id !== slotProps.value)" />
        </template>
      </p-multiselect>

      <div class="input date">
        <label class="borders"> 📅 Depuis
          <p-datepicker v-model="filters.date"></p-datepicker>
        </label>
      </div>

      <input class="borders" id="title" type="text" v-model="filters.title" placeholder="🔍 Titre">

      <AutoComplete 
        id="leader" 
        v-model="filters.leader" 
        :suggestions="leadersSearch.results" 
        :loading="leadersSearch.loading"
        @complete="fetchLeaders" 
        placeholder="🔍 Encadrant"
      />

      <div id="cancelled" class="toggle-button font-size-s"  @click="toggleCancelled" :class="{ enabled: filters.displayCancelled }">
        Sorties annulées :
        <span v-if="filters.displayCancelled" class="icon-button display-for-on">affichées <img src="/static/img/icon/ionicon/eye.svg" alt="&#128065"/></span>
        <span v-if="!filters.displayCancelled" class="icon-button display-for-off">cachées <img src="/static/img/icon/ionicon/eye-off.svg"/></span>
      </div>

    </template>
  </div>
  `
}