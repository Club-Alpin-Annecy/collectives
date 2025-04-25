const { inject } = Vue

export default {
  name: 'EventListItem',
  props: ["eventItem"],
  setup(props) {
    const config = inject('config')
    return {
      event: props.eventItem,
      EventStatus: config.models.EnumEventStatus
    }
  },
  methods: {
    freeslotPercent: function(event) {
        return 100-event.free_slots/event.num_slots*100 + '%'
    }
  },
  template: `
  <div
    ref="eventlist-item"
    class="tabulator-row tabulator-selectable"
    role="row"
  >
    <a
      class="row collectives-list--item"
      role="gridcell"
      :href="event.view_uri"
    >
      <div class="section collectives-list--item--photo">
        <img :src="event.photo_uri" />
      </div>
      <div class="section collectives-list--item--details">

        <!-- Card Header -->
        <div class="collectives-list--item--details-heading">
          <div class="no_mobile collectives-list--item--details-date">
            {{ event.formated_datetime_range }}
          </div>

          <div class="collectives-list--item--details-keywords">
          
            <span class="event-status-badge"
              v-if="!event.is_confirmed"
              :class="'event-status-'+ event.status"
            >
              {{EventStatus[event.status]}}
            </span>

            <span
              v-if="event.has_free_waiting_slots && !event.has_free_online_slots && event.status !== 'Cancelled'"
              class="event-status-badge event-status-waiting-list"
            >
              Liste d'attente
            </span>

            <span
              v-if="!event.has_free_slots && !event.has_free_waiting_slots && event.status !== 'Cancelled'"
              class="event-status-badge event-status-full">
              Complet
            </span>


          </div>

          <div>
            {{ event.title }}
          </div>
        </div>

        <!-- Card Bottom Left -->
        <div class="collectives-list--item--details-bottom-left">
          <div
            class="heading-3 no_mobile collectives-list--item--details-activity-type"
          >
            <img
              v-for="type in event.activity_types"
              :src="'/static/caf/icon/' + type.short + '.svg'"
              :alt="type.short"
              :title="type.short"
            />
          </div>

          <div
            class="mobile collectives-list--item--details-date"
          >
            {{ event.formated_datetime_range }}
          </div>
          <div
            class="leader collectives-list--item--details-leader"
          >
            <span v-for="(leader, index) in event.leaders.slice(0, 2)">
              {{ leader.full_name}}
              <br v-if="index < event.leaders.length" />
            </span>
          </div>
        </div>

        <!-- Bottom Right -->
        <div class="collectives-list--item--details-bottom-right">

          <!-- Tags -->
          <div class="collectives-list--item--details-tags">
          
            <span
              class="item inline-mobile aligned-flex-inline"
              v-for="type in event.activity_types"
            >
              <img
                width="30px"
                :src="'/static/caf/icon/' + type.short + '.svg'"
                :alt="type.short"
                :title="type.short" 
              />
              <span>{{ type.name }}</span>
            </span>

            <span class="item aligned-flex-inline">
              <img 
                :src="'/static/caf/icon/' + event.event_type.short + '.svg'"
                width="30px"
                :title="event.event_type.name"
              />
              <span>{{event.event_type.name}}</span>
            </span>

            <span class="item aligned-flex-inline" 
              v-for="tag in event.tags"> 
                <img 
                    :src="'/static/caf/icon/' + tag.short + '.svg'"
                    width="30px"
                    :title="tag.name"
                />
                <span>{{ tag.name }}</span>
            </span>

          </div>

          <!-- Slots -->
          <div class="collectives-list--item--details-slots">
            <div class="aligned-flex">
              <div
                class="collectives-list--item--details-slots-bar"
              >
                <div
                  class="collectives-list--item--details-slots-bar-filler"
                  :width="freeslotPercent(event)"
                  :style="{width: freeslotPercent(event)}"
                ></div>
            </div>
            <div
              collectives-list--item--details-slots-count=""
            >
              {{Math.max(0, event.occupied_slots)}}/{{event.num_slots}}
            </div>
          </div>

        </div>
      </div>
      </div>
    </a>
  </div>
  `,
};