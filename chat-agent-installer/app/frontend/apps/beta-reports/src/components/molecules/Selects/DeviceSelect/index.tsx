import { FC } from 'react';

import { StyledDeviceSelect } from './DeviceSelect.styled';

import { DeviceSelectProps } from './DeviceSelect.props';

const DeviceSelect: FC<DeviceSelectProps> = ({ className = '', ...props }) => {
  return (
    <StyledDeviceSelect
      className={`device-select ${className}`}
      showSearch
      allowClear
      placeholder='Select device'
      filterOption={(input, option) =>
        ((option?.label as string) ?? '')
          .toLowerCase()
          .includes(input.toLowerCase())
      }
      {...props}
    />
  );
};

export default DeviceSelect;
