import { FC } from 'react';
import { DatePicker } from 'antd';
const { RangePicker } = DatePicker;

import { CustomRangePickerProps } from '@shared/ui/components/atoms/DatePickers/CustomRangePicker/CustomRangePicker.props';

const CustomRangePicker: FC<CustomRangePickerProps> = (props) => {
  return <RangePicker {...props} />;
};

export default CustomRangePicker;
