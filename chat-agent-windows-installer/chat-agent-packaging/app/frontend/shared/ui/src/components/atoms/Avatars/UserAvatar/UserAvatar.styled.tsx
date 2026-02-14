import styled from 'styled-components';
import { Avatar } from 'antd';

export const StyledUserAvatar = styled(Avatar)`
  &.ant-avatar {
    background-color: ${({ theme }) => theme?.colors?.primary || '#fc1c39'};
    color: ${({ theme }) => theme?.colors?.grey || '#f9f9f9'};
  }
`;
