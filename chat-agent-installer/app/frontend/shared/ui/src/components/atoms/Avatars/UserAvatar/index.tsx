import { FC, useMemo } from 'react';

import { StyledUserAvatar } from '@shared/ui/components/atoms/Avatars/UserAvatar/UserAvatar.styled';

import { UserAvatarProps } from '@shared/ui/components/atoms/Avatars/UserAvatar/UserAvatar.props';

const UserAvatar: FC<UserAvatarProps> = ({
  className = '',
  userEmail = '',
  ...props
}) => {
  const name = useMemo(() => {
    if (!userEmail?.length) {
      return '';
    }
    const [fullName = ''] = userEmail.split('@');
    const [firstName = '', lastName = ''] = fullName.split('.');
    return `${firstName[0]?.toUpperCase()}${lastName[0]?.toUpperCase()}`;
  }, [userEmail]);

  return (
    <StyledUserAvatar
      data-testid='user-avatar'
      className={`user-avatar ${className}`}
      {...props}
    >
      {name}
    </StyledUserAvatar>
  );
};

export default UserAvatar;
