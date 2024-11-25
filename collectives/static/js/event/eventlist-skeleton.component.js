export default {
  name: 'EventListSkeleton',
  setup(props) {
  },
  template: `
  <div
    class="tabulator-row tabulator-selectable"
  >
    <div
      class="row collectives-list--item"
    >
      <div class="section collectives-list--item--photo">
        <Skeleton width="277.5px" height="185px"></Skeleton>
      </div>
      <div class="section collectives-list--item--details">

        <!-- Card Header -->
        <div class="collectives-list--item--details-heading">
          <div class="no_mobile collectives-list--item--details-date">
            <Skeleton></Skeleton>
          </div>

          <div>
            <Skeleton></Skeleton>
          </div>
        </div>

        <!-- Card Bottom Left -->
        <div class="collectives-list--item--details-bottom-left">
          <div
            class="heading-3 no_mobile collectives-list--item--details-activity-type"
          >
            <Skeleton shape="circle" width="65px" height="65px"></Skeleton>
          </div>

          <div
            class="mobile collectives-list--item--details-date"
          >
            <Skeleton></Skeleton>
          </div>
          <div
            class="leader collectives-list--item--details-leader"
          >
            <Skeleton></Skeleton>
          </div>
        </div>

        <!-- Bottom Right -->
        <div class="collectives-list--item--details-bottom-right">


          <!-- Slots -->
          <div class="collectives-list--item--details-slots">
            <div class="aligned-flex">
              <div
                class="collectives-list--item--details-slots-bar"
              >
                <Skeleton>
                  class="collectives-list--item--details-slots-bar-filler"
                ></Skeleton>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  `,
};