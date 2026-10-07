const { ref, computed, inject } = Vue

/**
 * Filter value meaning "no activity checked". Unknown by the API, it matches no event.
 */
const NONE = '__none'

/**
 * Legacy filter value, from when services were grouped in a single choice.
 * Still accepted by the API; replaced by the list of services when found in a saved filter.
 */
const LEGACY_SERVICES = '__services'

/**
 * Activity selector displayed as one column per activity kind (activités, initiatives, services).
 *
 * The model is the list of selected activity short names. An empty list means
 * "no filter", which is displayed as every box being checked.
 */
export default {
  props: ['modelValue'],
  emits: ['update:modelValue'],

  setup(props, { emit }) {
    const config = inject('config')
    const popover = ref(null)

    const groups = config.activityGroups
    const items = groups.flatMap(group => group.items)
    const allIds = items.map(item => item.id)
    const itemsById = Object.fromEntries(items.map(item => [item.id, item]))

    const selected = computed(() => {
      const value = props.modelValue || []
      if (value.length === 0) return new Set(allIds)
      return new Set(value.filter(id => id in itemsById))
    })

    function update(selection) {
      if (allIds.every(id => selection.has(id))) {
        emit('update:modelValue', [])
      } else if (selection.size === 0) {
        emit('update:modelValue', [NONE])
      } else {
        emit('update:modelValue', allIds.filter(id => selection.has(id)))
      }
    }

    function toggleItem(id) {
      const selection = new Set(selected.value)
      selection.has(id) ? selection.delete(id) : selection.add(id)
      update(selection)
    }

    function groupState(group) {
      const count = group.items.filter(item => selected.value.has(item.id)).length
      if (count === 0) return 'none'
      return count === group.items.length ? 'all' : 'some'
    }

    function toggleGroup(group) {
      const selection = new Set(selected.value)
      const check = groupState(group) !== 'all'
      group.items.forEach(item => check ? selection.add(item.id) : selection.delete(item.id))
      update(selection)
    }

    // Le filtre est restauré du localStorage : on remplace l'ancien choix « Services »
    // par la liste des services, et on retire les activités qui n'existent plus.
    const saved = props.modelValue || []
    if (!(saved.length === 1 && saved[0] === NONE)) {
      const services = groups.find(group => group.kind === 'Service')?.items.map(item => item.id) || []
      const known = saved
        .flatMap(id => (id === LEGACY_SERVICES ? services : [id]))
        .filter(id => id in itemsById)
      if (known.length !== saved.length || known.some((id, i) => id !== saved[i])) {
        known.length === 0 ? emit('update:modelValue', []) : update(new Set(known))
      }
    }

    const MAX_CHIPS = 3
    const chips = computed(() => {
      if (selected.value.size === allIds.length || selected.value.size > MAX_CHIPS) return []
      return allIds.filter(id => selected.value.has(id)).map(id => itemsById[id])
    })
    const summary = computed(() => {
      if (selected.value.size === allIds.length) return 'Toutes activités'
      if (selected.value.size === 0) return 'Aucune activité'
      if (chips.value.length > 0) return ''
      return `${selected.value.size} activités sur ${allIds.length}`
    })

    return {
      popover,
      groups,
      selected,
      chips,
      summary,
      toggle: (event) => popover.value.toggle(event),
      toggleItem,
      toggleGroup,
      groupState,
      checkAll: () => update(new Set(allIds)),
      uncheckAll: () => update(new Set()),
      iconUrl: (item) => `/static/caf/icon/${item.icon}.svg`,
    }
  },

  template: `
    <div class="activity-filter">
      <div class="activity-filter-trigger" role="button" tabindex="0" aria-haspopup="true"
        aria-label="Filtrer par activité"
        @click="toggle" @keydown.enter="toggle" @keydown.space.prevent="toggle">
        <span class="activity-filter-trigger-label">
          <span v-if="summary">{{ summary }}</span>
          <Chip
            v-for="item in chips"
            :key="item.id"
            :label="item.name"
            :image="iconUrl(item)"
            removable
            @remove="toggleItem(item.id)"
            @click.stop
          />
        </span>
        <i class="pi pi-chevron-down"></i>
      </div>

      <Popover ref="popover">
        <div class="activity-filter-panel">
          <div class="activity-filter-columns" :style="{ '--columns': groups.length }">
            <div class="activity-filter-column" v-for="group in groups" :key="group.kind">
              <label class="activity-filter-group">
                <input
                  type="checkbox"
                  :checked="groupState(group) === 'all'"
                  :indeterminate="groupState(group) === 'some'"
                  @change="toggleGroup(group)"
                />
                {{ group.label }}
              </label>
              <label class="activity-filter-item" v-for="item in group.items" :key="item.id">
                <input
                  type="checkbox"
                  :checked="selected.has(item.id)"
                  @change="toggleItem(item.id)"
                />
                <img class="icon" :src="iconUrl(item)" alt="" />
                {{ item.name }}
              </label>
            </div>
          </div>
          <div class="activity-filter-footer">
            <Button label="Tout décocher" severity="secondary" text size="small" @click="uncheckAll" />
            <Button label="Tout cocher" text size="small" @click="checkAll" />
          </div>
        </div>
      </Popover>
    </div>
  `
}
