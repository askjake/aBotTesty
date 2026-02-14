import { FC } from 'react';

import { StyledIconButton } from '@shared/ui/components/atoms/Buttons/IconButton/IconButton.styled';

import { IconButtonProps } from '@shared/ui/components/atoms/Buttons/IconButton/IconButton.props';

const IconButton: FC<IconButtonProps> = (props) => (
  <StyledIconButton {...props} />
);

export default IconButton;
