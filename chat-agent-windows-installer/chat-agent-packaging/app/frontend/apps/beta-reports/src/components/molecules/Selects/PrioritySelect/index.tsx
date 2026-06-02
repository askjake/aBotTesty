import { FC } from 'react';

import { StyledPrioritySelect } from './PrioritySelect.styled';

import { PrioritySelectProps } from './PrioritySelect.props';

const priorityOptions = [
  { label: 'Test Activity', value: 0 },
  ...Array.from({ length: 5 }, (_, x) => ({
    label: `P${x + 1}`,
    value: x + 1,
  })),
];

const PrioritySelect: FC<PrioritySelectProps> = ({
  className = '',
  ...props
}) => {
  return (
    <StyledPrioritySelect
      className={`priority-select ${className}`}
      options={priorityOptions}
      allowClear
      {...props}
    />
  );
};

export default PrioritySelect;
