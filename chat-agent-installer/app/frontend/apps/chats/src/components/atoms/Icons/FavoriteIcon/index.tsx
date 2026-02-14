import { FC } from 'react';

import {
  StyledActiveFavoriteIcon,
  StyledInactiveFavoriteIcon,
} from '@/components/atoms/Icons/FavoriteIcon/FavoriteIcon.styled';

import { FavoriteIconProps } from '@/components/atoms/Icons/FavoriteIcon/FavoriteIcon.props';

const FavoriteIcon: FC<FavoriteIconProps> = ({
  active = false,
  className = '',
  ...props
}) => {
  return active ? (
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    <StyledActiveFavoriteIcon
      data-testid='active-star-icon'
      className={`star-icon ${className}`}
      {...props}
    />
  ) : (
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    <StyledInactiveFavoriteIcon
      data-testid='inactive-star-icon'
      className={`star-icon ${className}`}
      {...props}
    />
  );
};

export default FavoriteIcon;
