import { BubbleProps } from '@ant-design/x';

import { FC } from 'react';

import { StyledCustomBubble } from '@shared/ui/components/atoms/Bubbles/CustomBubble/CustomBubble.styled';

const CustomBubble: FC<BubbleProps> = ({ className = '', ...props }) => {
  return (
    <StyledCustomBubble className={`custom-bubble ${className}`} {...props} />
  );
};

export default CustomBubble;
