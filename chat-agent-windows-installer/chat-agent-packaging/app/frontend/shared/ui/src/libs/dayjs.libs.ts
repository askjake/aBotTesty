import dayjs from 'dayjs';

import timezone from 'dayjs/plugin/timezone';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
// import objectSupport from 'dayjs/plugin/objectSupport';
// import customParseFormat from 'dayjs/plugin/customParseFormat';
// import utc from 'dayjs/plugin/utc';
// import localeData from 'dayjs/plugin/localeData';
// import weekday from 'dayjs/plugin/weekday';
// import dayOfYear from 'dayjs/plugin/dayOfYear';
// import isBetween from 'dayjs/plugin/isBetween';
// import isoWeek from 'dayjs/plugin/isoWeek';
// import weekOfYear from 'dayjs/plugin/weekOfYear';
// import localizedFormat from 'dayjs/plugin/localizedFormat';

// dayjs.extend(objectSupport);
// dayjs.extend(customParseFormat);
// dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);
dayjs.extend(isToday);
dayjs.extend(isYesterday);
// dayjs.extend(localeData);
// dayjs.extend(weekday);
// dayjs.extend(dayOfYear);
// dayjs.extend(weekOfYear);
// dayjs.extend(isBetween);
// dayjs.extend(isoWeek);
// dayjs.extend(isSameOrAfter);
// dayjs.extend(isSameOrBefore);
// dayjs.extend(isToday);
// dayjs.extend(localizedFormat);

dayjs.tz.setDefault('America/Denver');

const customDayjs = dayjs;

export default customDayjs;
