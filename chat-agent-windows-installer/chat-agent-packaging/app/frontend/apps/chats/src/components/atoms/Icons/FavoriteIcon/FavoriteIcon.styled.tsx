import styled from 'styled-components';
import { BsBookmarkCheck, BsBookmarkCheckFill } from 'react-icons/bs';

export const StyledActiveFavoriteIcon = styled(BsBookmarkCheckFill)`
  color: ${({ theme }) => theme?.colors?.primary || '#fc1c39'};
`;

export const StyledInactiveFavoriteIcon = styled(BsBookmarkCheck)``;
