import styled from 'styled-components';
import { SafetyCertificateFilled } from '@ant-design/icons';

export const StyledVaultModeButtonIcon = styled(SafetyCertificateFilled)<{
  $active: boolean;
}>`
  &.anticon-safety-certificate {
    color: ${({ $active = false, theme }) =>
      $active ? theme?.colors?.green || '#34d399' : theme?.colors?.primary || '#fc1c39'};
  }
`;
