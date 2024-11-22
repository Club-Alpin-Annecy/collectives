import EventListItem from './eventlist-item.component.js'
import EventListFilters from './eventlist-filters.component.js'
import { getEvents } from '../api.js'
import moment from 'moment'
import EventListSkeleton from './eventlist-skeleton.component.js'

const { ref, watch, reactive, inject, onMounted, useTemplateRef } = Vue

export default {
    setup() {
        // Compute Starting Page
        const pageNumberRegex = /#(\d+)/;
        const pageNumberMatch = window.location.hash.match(pageNumberRegex)
        const startingPage = pageNumberMatch && pageNumberMatch[1] ? Number(pageNumberMatch[1]) : 1

        const config = inject('config')
        const loading = ref(false)
        const events = ref([])
        const eventCount = ref(0)
        const eventlistRefEl = useTemplateRef('eventlist')

        const eventParams = reactive({
            page: startingPage,
            pageSize: 25,
            first: (startingPage - 1) * 25 + 1,
        })

        const eventFilters = reactive({
            activities: localStorage.getItem('eventlist-filters') ? JSON.parse(localStorage.getItem('eventlist-filters')).activities : [],
            eventTypes: localStorage.getItem('eventlist-filters') ? JSON.parse(localStorage.getItem('eventlist-filters')).eventTypes : [],
            eventTags: localStorage.getItem('eventlist-filters') ? JSON.parse(localStorage.getItem('eventlist-filters')).eventTags : [],
            date: moment().format("DD/MM/YYYY"),
            title: null,
            leader: null,
            displayCancelled: localStorage.getItem('eventlist-filters') ? JSON.parse(localStorage.getItem('eventlist-filters')).displayCancelled : false
        })

        function saveFiltersToLocalStorage(){
            localStorage.setItem('eventlist-filters', JSON.stringify(eventFilters))
        }
        watch(eventFilters, (filters) => saveFiltersToLocalStorage(filters))


        function groupByDate(events) {
            return events.reduce((acc, event) => {
                const date = moment(event.start).format("dddd Do MMMM YYYY")
                if(!acc[date]) acc[date] = []
                acc[date].push(event)
                return acc
            }, {})
        }

        /**
         * Watch for changes in eventParams and eventFilters
         * Set Loaders and request the events for the given parameters and filters
         */
        watch([eventParams, eventFilters], async ([params, filters]) => {
            loading.value = true
            const { data } = await getEvents(params, filters)
            events.value = groupByDate(data.data)
            // TODO Improve API
            eventCount.value = data.last_page * params.pageSize
            loading.value = false
        }, { immediate: true })



        function setPaginator(pageState) {
            const pageNumber = pageState.page + 1
            eventParams.page = pageNumber
            eventParams.pageSize = pageState.rows
            eventParams.first = pageState.page * pageState.rows + 1
            history.pushState(null,null,'#' + pageNumber);
        }

        /**
         * Smooth scroll to the top of the event list
         */
        function gotoEvents() {
            eventlistRefEl.value.scrollIntoView({ behavior: 'smooth' }) 
        }

        onMounted(() => {
                gotoEvents()
        })

        return { 
            events,
            config,
            IsLoading: () => loading.value,
            eventParams,
            eventFilters,
            eventCount,
            setPaginator,
            gotoEvents,
        }
    },
    components: {
        EventListItem,
        EventListFilters,
        EventListSkeleton
    },
    template: `
        <div id="cover">
            <div>
                <img
                    :src="config.siteParams.coverLogo"
                    class="motto"
                />
                <br />
                <img
                    :src="config.siteParams.arrowDown"
                    class="arrow"
                    @click="gotoEvents()"
                />
            </div>
        </div>
        <div ref="eventlist" id="eventlist" class="page-content">
            <div id="banner-message" v-if="config.siteParams.bannerMessage">
                <h5 class="heading-1">Message important</h5>
                <div v-html="config.siteParams.bannerMessage" />
            </div>
            <div class="collectives-list tabulator">

                <EventListFilters v-bind:filters="eventFilters"/>

                <template v-if="IsLoading()">
                    <EventListSkeleton v-for="n in 5" v-bind:eventItem="null" :key="n"/>
                </template>


                <Accordion v-if="!IsLoading()" multiple :value="Object.keys(events)">
                    <AccordionPanel :value="date" header="Header" toggleable v-for="(dateEvents, date) in events">
                        <AccordionHeader>
                            {{ date }}
                        </AccordionHeader>
                        <AccordionContent>
                            <EventListItem v-for="eventItem in dateEvents" v-bind:eventItem="eventItem" :key="eventItem.id"/>
                        </AccordionContent>
                    </AccordionPanel>
                </Accordion>

                <Paginator 
                    @page="setPaginator"
                    :first="eventParams.first"
                    :totalRecords="eventCount" 
                    :rows="eventParams.pageSize" 
                    :rowsPerPageOptions="[25, 50, 100]"
                ></Paginator>

            </div>
        </div>
    `,
}