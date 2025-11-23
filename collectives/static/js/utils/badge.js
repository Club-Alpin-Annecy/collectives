
function updateBadgeLevels(
    badgeLevels,
    badgeSelect,
    badgeActivityIdSelect,
    levelSelect
) {
    while (levelSelect.options.length > 0) {
        levelSelect.remove(0);
    }
    const badgeId = badgeSelect.value;
    const activityId = badgeActivityIdSelect.value;
    hidden = true;

    var levels = {};
    if (badgeId in badgeLevels) {
        var thisBadgeLevels = badgeLevels[badgeId]
        if (activityId in thisBadgeLevels) {

            for (const [key, level] of Object.entries(thisBadgeLevels[null])) {
                // Default levels
                // Only add if it is not activity-specific but accepts activities
                if (level.activity_id == null && level.accepts_activity) {
                    levels[key] = level
                }
            }

            Object.assign(levels, thisBadgeLevels[activityId])

        } else {
            for (const [key, level] of Object.entries(thisBadgeLevels[null])) {
                // Default levels
                // Only add if it is not activity-specific
                if (level.activity_id == null) {
                    levels[key] = level
                }
            }
        }

    }

    if (Object.entries(levels).length == 0) {
        levels = {"": {name: "Aucun"}};
    }
    for (const [key, level] of Object.entries(levels)) {
        const option = document.createElement("option");
        option.value = key;
        option.text = level.name;
        levelSelect.add(option);

        hidden = false;
    }

    levelSelect.style.display = hidden ? "none" : "inline-block";
}