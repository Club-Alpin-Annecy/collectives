
import axios from 'axios'

export async function searchLeaders(leaderNameQuery, resultLimit = 8) {
  const res = await axios.get(
    '/api/leaders/autocomplete/', 
    {
      params: {
          q: leaderNameQuery,
          l: resultLimit,
      }
  })
  return res
}

export async function getEvents(pageParam, filters) {

  const res = await axios.get(
    '/api/events/', 
    {
      params: {
          page: pageParam.page,
          size: pageParam.pageSize,
          filters: filtersToQuery(filters),
      }
  })
  return res
}

function filtersToQuery(filters) {
  const filterPayload = []

  if (filters.title) {
    filterPayload.push({ field: 'title', type: 'like', value: filters.title })
  }

  filterPayload.push({ field: 'end', type: 'like', value: 
    filters.date || getServerLocalTime()
  })

  if (filters.leader) {
    filterPayload.push({ field: 'leaders', type: 'like', value: 
      filters.leader
    })
  }
  
  if (!filters.displayCancelled) { 
    filterPayload.push({ field: 'status', type: '!=', value: 'Cancelled' })
  }

  if(filters.activities?.length > 0) {
    filterPayload.push(...
      filters.activities.map(activity => ({
        field: 'activity_type',type: '=', value: activity
      }))
    )
  }

  if(filters.eventTypes?.length > 0) {
    filterPayload.push(...
      filters.eventTypes.map(value => ({
        field: 'event_type',type: '=', value
      }))
    )
  }

  if(filters.eventTags?.length > 0) {
    filterPayload.push(...
      filters.eventTags.map(value => ({
        field: 'tags',type: '=', value
      }))
    )
  }

  return filterPayload
}