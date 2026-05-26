import { FC } from 'react';

import { StyledPlatformSelect } from './PlatformSelect.styled';

import { PlatformSelectProps } from './PlatformSelect.props';

const PlatformSelect: FC<PlatformSelectProps> = ({
  className = '',
  ...props
}) => {
  return (
    <StyledPlatformSelect
      className={`platform-select ${className}`}
      showSearch
      placeholder='Select platform'
      filterOption={(input, option) =>
        ((option?.label as string) ?? '')
          .toLowerCase()
          .includes(input.toLowerCase())
      }
      {...props}
    />
  );
};

export default PlatformSelect;
